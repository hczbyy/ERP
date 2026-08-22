package com.openerp.service;

import com.openerp.audit.AuditService;
import com.openerp.common.BusinessException;
import com.openerp.common.PageResult;
import com.openerp.dto.OrderRequests;
import com.openerp.entity.*;
import com.openerp.repository.*;
import com.openerp.util.BillNoGenerator;
import com.openerp.util.Rows;
import com.openerp.util.Validators;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

@Service
public class PurchaseService {
    private final PoOrderRepository orderRepository;
    private final PoStockInRepository stockInRepository;
    private final MdSupplierRepository supplierRepository;
    private final MdWarehouseRepository warehouseRepository;
    private final MdProductRepository productRepository;
    private final FinPayableRepository payableRepository;
    private final InventoryService inventoryService;
    private final BillNoGenerator billNoGenerator;
    private final AuditService auditService;

    public PurchaseService(PoOrderRepository orderRepository,
                           PoStockInRepository stockInRepository,
                           MdSupplierRepository supplierRepository,
                           MdWarehouseRepository warehouseRepository,
                           MdProductRepository productRepository,
                           FinPayableRepository payableRepository,
                           InventoryService inventoryService,
                           BillNoGenerator billNoGenerator,
                           AuditService auditService) {
        this.orderRepository = orderRepository;
        this.stockInRepository = stockInRepository;
        this.supplierRepository = supplierRepository;
        this.warehouseRepository = warehouseRepository;
        this.productRepository = productRepository;
        this.payableRepository = payableRepository;
        this.inventoryService = inventoryService;
        this.billNoGenerator = billNoGenerator;
        this.auditService = auditService;
    }

    private void ensureRelations(Long supplierId, Long warehouseId, List<Long> productIds) {
        if (!supplierRepository.existsById(supplierId)) {
            throw new BusinessException("供应商不存在，请刷新后重试");
        }
        if (!warehouseRepository.existsById(warehouseId)) {
            throw new BusinessException("仓库不存在，请刷新后重试");
        }
        List<Long> ids = new ArrayList<>(new LinkedHashSet<>(productIds));
        if (ids.isEmpty()) {
            throw new BusinessException("采购单至少需要一条商品明细");
        }
        Set<Long> found = new HashSet<>();
        for (MdProduct p : productRepository.findAllById(ids)) found.add(p.getId());
        List<Long> missing = ids.stream().filter(i -> !found.contains(i)).toList();
        if (!missing.isEmpty()) {
            throw new BusinessException("商品不存在: " + missing);
        }
    }

    private BigDecimal fillItems(PoOrder order, List<OrderRequests.OrderItem> items) {
        BigDecimal total = BigDecimal.ZERO;
        order.getItems().clear();
        for (OrderRequests.OrderItem it : items) {
            BigDecimal qty = Validators.requireIntQty(it.qty(), it.productId(), "数量");
            BigDecimal price = it.price();
            if (price == null || price.signum() < 0) {
                throw new BusinessException("商品 #" + it.productId() + " 单价不能为负");
            }
            BigDecimal amount = qty.multiply(price);
            total = total.add(amount);
            PoOrderItem item = new PoOrderItem();
            item.setProductId(it.productId());
            item.setQty(qty);
            item.setPrice(price);
            item.setAmount(amount);
            item.setOrder(order);
            order.getItems().add(item);
        }
        return total;
    }

    @Transactional
    public PoOrder createOrder(OrderRequests.PurchaseOrderBody body, String username) {
        List<OrderRequests.OrderItem> items = body.items() == null ? List.of() : body.items();
        if (items.isEmpty()) {
            throw new BusinessException("采购单至少需要一条商品明细");
        }
        ensureRelations(body.supplierId(), body.warehouseId(),
                items.stream().map(OrderRequests.OrderItem::productId).toList());
        PoOrder order = new PoOrder();
        order.setOrderNo(billNoGenerator.gen("purchase_order"));
        order.setSupplierId(body.supplierId());
        order.setWarehouseId(body.warehouseId());
        order.setRemark(body.remark());
        order.setCreatedBy(username);
        order.setTotalAmount(fillItems(order, items));
        return orderRepository.save(order);
    }

    @Transactional
    public PoOrder updateOrder(Long id, OrderRequests.PurchaseOrderBody body, String username) {
        PoOrder order = getOrder(id);
        if (!"draft".equals(order.getStatus())) {
            throw new BusinessException("仅草稿状态可修改，当前状态: " + statusText(order.getStatus()));
        }
        List<OrderRequests.OrderItem> items = body.items() == null ? List.of() : body.items();
        if (items.isEmpty()) {
            throw new BusinessException("采购单至少需要一条商品明细");
        }
        ensureRelations(body.supplierId(), body.warehouseId(),
                items.stream().map(OrderRequests.OrderItem::productId).toList());
        order.setSupplierId(body.supplierId());
        order.setWarehouseId(body.warehouseId());
        order.setRemark(body.remark());
        order.setTotalAmount(fillItems(order, items));
        return orderRepository.save(order);
    }

    @Transactional
    public PoOrder approveOrder(Long id, String username) {
        PoOrder order = getOrder(id);
        if (!"draft".equals(order.getStatus())) {
            throw new BusinessException("只有草稿状态的采购单才能审核，当前状态: " + order.getStatus());
        }
        order.setStatus("approved");
        order.setApprovedBy(username);
        order.setApprovedAt(LocalDate.now());
        return orderRepository.save(order);
    }

    @Transactional
    public PoOrder cancelOrder(Long id, String reason, String username) {
        PoOrder order = getOrder(id);
        if (!List.of("draft", "approved").contains(order.getStatus())) {
            throw new BusinessException("当前状态 " + order.getStatus() + " 不允许取消");
        }
        order.setStatus("cancelled");
        order.setCancelReason(reason == null || reason.isBlank() ? "未说明" : reason);
        return orderRepository.save(order);
    }

    @Transactional
    public PoStockIn receiveOrder(Long id, OrderRequests.ReceiveShipBody body, String username) {
        PoOrder order = getOrder(id);
        if (!List.of("approved", "partially_received").contains(order.getStatus())) {
            throw new BusinessException("只有已审核的采购单才能收货，当前状态: " + order.getStatus());
        }
        List<OrderRequests.OrderItem> items = body.items() == null ? List.of() : body.items();
        if (items.isEmpty()) {
            throw new BusinessException("收货明细不能为空");
        }
        Map<Long, PoOrderItem> itemMap = new HashMap<>();
        for (PoOrderItem it : order.getItems()) itemMap.put(it.getProductId(), it);
        for (OrderRequests.OrderItem b : items) {
            BigDecimal qty = Validators.requireIntQty(b.qty(), b.productId(), "收货数量");
            BigDecimal price = b.price();
            if (price == null || price.signum() < 0) {
                throw new BusinessException("收货单价不能为负");
            }
            PoOrderItem poItem = itemMap.get(b.productId());
            if (poItem == null) {
                throw new BusinessException("商品 #" + b.productId() + " 不在采购单中");
            }
            BigDecimal remain = poItem.getQty().subtract(poItem.getReceivedQty());
            if (qty.compareTo(remain) > 0) {
                throw new BusinessException("商品「" + poItem.getProduct().getName()
                        + "」收货数量 " + qty.stripTrailingZeros().toPlainString()
                        + " 超过未收数量 " + remain.stripTrailingZeros().toPlainString());
            }
        }

        PoStockIn stockIn = new PoStockIn();
        stockIn.setStockInNo(billNoGenerator.gen("stock_in"));
        stockIn.setPoId(order.getId());
        stockIn.setPoNo(order.getOrderNo());
        stockIn.setSupplierId(order.getSupplierId());
        stockIn.setWarehouseId(order.getWarehouseId());
        stockIn.setRemark(body.remark());
        stockIn.setCreatedBy(username);
        BigDecimal total = BigDecimal.ZERO;
        for (OrderRequests.OrderItem b : items) {
            BigDecimal qty = Validators.requireIntQty(b.qty(), b.productId(), "收货数量");
            PoOrderItem poItem = itemMap.get(b.productId());
            BigDecimal price = b.price();
            BigDecimal amount = qty.multiply(price);
            total = total.add(amount);
            poItem.setReceivedQty(poItem.getReceivedQty().add(qty));
            PoStockInItem siItem = new PoStockInItem();
            siItem.setProductId(b.productId());
            siItem.setQty(qty);
            siItem.setPrice(price);
            siItem.setAmount(amount);
            siItem.setStockIn(stockIn);
            stockIn.getItems().add(siItem);
            inventoryService.changeStock(b.productId(), order.getWarehouseId(), qty,
                    "purchase_in", stockIn.getStockInNo(), username, "采购入库 " + order.getOrderNo());
        }
        stockIn.setTotalAmount(total);
        stockInRepository.save(stockIn);

        FinPayable payable = new FinPayable();
        payable.setPayableNo(billNoGenerator.gen("payable"));
        payable.setSourceNo(stockIn.getStockInNo());
        payable.setSupplierId(order.getSupplierId());
        payable.setTotalAmount(total);
        payable.setDueDate(LocalDate.now());
        payable.setRemark("采购入库 " + order.getOrderNo());
        payable.setCreatedBy(username);
        payableRepository.save(payable);

        boolean allReceived = order.getItems().stream()
                .allMatch(it -> it.getReceivedQty().compareTo(it.getQty()) >= 0);
        order.setStatus(allReceived ? "completed" : "partially_received");
        orderRepository.save(order);
        return stockIn;
    }

    @Transactional
    public void deleteOrder(Long id, String username, String ip) {
        PoOrder order = getOrder(id);
        if (!"draft".equals(order.getStatus())) {
            throw new BusinessException("仅草稿状态可删除");
        }
        orderRepository.delete(order);
        auditService.write(username, "delete", "purchase", order.getOrderNo(), null, ip);
    }

    @Transactional(readOnly = true)
    public PoOrder getOrder(Long id) {
        return orderRepository.findWithItemsById(id)
                .orElseThrow(() -> new BusinessException("采购单不存在"));
    }

    @Transactional(readOnly = true)
    public PageResult pageOrders(String status, String keyword, int pageNo, int pageSize) {
        Page<PoOrder> p = orderRepository.search(status, keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::poOrder).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> orderDetail(Long id) {
        PoOrder order = getOrder(id);
        Map<String, Object> data = Rows.poOrder(order);
        data.put("items", order.getItems().stream().map(Rows::poItem).toList());
        return data;
    }

    @Transactional(readOnly = true)
    public PageResult pageStockIns(String keyword, int pageNo, int pageSize) {
        Page<PoStockIn> p = stockInRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::poStockIn).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> stockInDetail(Long id) {
        PoStockIn si = stockInRepository.findById(id)
                .orElseThrow(() -> new BusinessException("入库单不存在"));
        Map<String, Object> data = Rows.poStockIn(si);
        data.put("items", si.getItems().stream().map(Rows::poStockInItem).toList());
        return data;
    }

    private static String statusText(String status) {
        return switch (status) {
            case "draft" -> "草稿";
            case "approved" -> "已审核";
            case "partially_received" -> "部分收货";
            case "completed" -> "已完成";
            case "cancelled" -> "已取消";
            default -> status;
        };
    }
}
