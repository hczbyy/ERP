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
public class SalesService {
    private final SoOrderRepository orderRepository;
    private final SoStockOutRepository stockOutRepository;
    private final MdCustomerRepository customerRepository;
    private final MdWarehouseRepository warehouseRepository;
    private final MdProductRepository productRepository;
    private final FinReceivableRepository receivableRepository;
    private final InventoryService inventoryService;
    private final BillNoGenerator billNoGenerator;
    private final AuditService auditService;

    public SalesService(SoOrderRepository orderRepository,
                        SoStockOutRepository stockOutRepository,
                        MdCustomerRepository customerRepository,
                        MdWarehouseRepository warehouseRepository,
                        MdProductRepository productRepository,
                        FinReceivableRepository receivableRepository,
                        InventoryService inventoryService,
                        BillNoGenerator billNoGenerator,
                        AuditService auditService) {
        this.orderRepository = orderRepository;
        this.stockOutRepository = stockOutRepository;
        this.customerRepository = customerRepository;
        this.warehouseRepository = warehouseRepository;
        this.productRepository = productRepository;
        this.receivableRepository = receivableRepository;
        this.inventoryService = inventoryService;
        this.billNoGenerator = billNoGenerator;
        this.auditService = auditService;
    }

    private void ensureRelations(Long customerId, Long warehouseId, List<Long> productIds) {
        if (!customerRepository.existsById(customerId)) {
            throw new BusinessException("客户不存在，请刷新后重试");
        }
        if (!warehouseRepository.existsById(warehouseId)) {
            throw new BusinessException("仓库不存在，请刷新后重试");
        }
        List<Long> ids = new ArrayList<>(new LinkedHashSet<>(productIds));
        if (ids.isEmpty()) {
            throw new BusinessException("销售单至少需要一条商品明细");
        }
        Set<Long> found = new HashSet<>();
        for (MdProduct p : productRepository.findAllById(ids)) found.add(p.getId());
        List<Long> missing = ids.stream().filter(i -> !found.contains(i)).toList();
        if (!missing.isEmpty()) {
            throw new BusinessException("商品不存在: " + missing);
        }
    }

    private BigDecimal fillItems(SoOrder order, List<OrderRequests.OrderItem> items) {
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
            SoOrderItem item = new SoOrderItem();
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
    public SoOrder createOrder(OrderRequests.SalesOrderBody body, String username) {
        List<OrderRequests.OrderItem> items = body.items() == null ? List.of() : body.items();
        if (items.isEmpty()) {
            throw new BusinessException("销售单至少需要一条商品明细");
        }
        ensureRelations(body.customerId(), body.warehouseId(),
                items.stream().map(OrderRequests.OrderItem::productId).toList());
        SoOrder order = new SoOrder();
        order.setOrderNo(billNoGenerator.gen("sales_order"));
        order.setCustomerId(body.customerId());
        order.setWarehouseId(body.warehouseId());
        order.setRemark(body.remark());
        order.setCreatedBy(username);
        order.setTotalAmount(fillItems(order, items));
        return orderRepository.save(order);
    }

    @Transactional
    public SoOrder updateOrder(Long id, OrderRequests.SalesOrderBody body, String username) {
        SoOrder order = getOrder(id);
        if (!"draft".equals(order.getStatus())) {
            throw new BusinessException("仅草稿状态可修改，当前状态: " + statusText(order.getStatus()));
        }
        List<OrderRequests.OrderItem> items = body.items() == null ? List.of() : body.items();
        if (items.isEmpty()) {
            throw new BusinessException("销售单至少需要一条商品明细");
        }
        ensureRelations(body.customerId(), body.warehouseId(),
                items.stream().map(OrderRequests.OrderItem::productId).toList());
        order.setCustomerId(body.customerId());
        order.setWarehouseId(body.warehouseId());
        order.setRemark(body.remark());
        order.setTotalAmount(fillItems(order, items));
        return orderRepository.save(order);
    }

    @Transactional
    public SoOrder approveOrder(Long id, String username) {
        SoOrder order = getOrder(id);
        if (!"draft".equals(order.getStatus())) {
            throw new BusinessException("只有草稿状态的销售单才能审核，当前状态: " + order.getStatus());
        }
        order.setStatus("approved");
        order.setApprovedBy(username);
        order.setApprovedAt(LocalDate.now());
        return orderRepository.save(order);
    }

    @Transactional
    public SoOrder cancelOrder(Long id, String reason, String username) {
        SoOrder order = getOrder(id);
        if (!List.of("draft", "approved").contains(order.getStatus())) {
            throw new BusinessException("当前状态 " + order.getStatus() + " 不允许取消");
        }
        order.setStatus("cancelled");
        order.setCancelReason(reason == null || reason.isBlank() ? "未说明" : reason);
        return orderRepository.save(order);
    }

    @Transactional
    public SoStockOut shipOrder(Long id, OrderRequests.ReceiveShipBody body, String username) {
        SoOrder order = getOrder(id);
        if (!List.of("approved", "partially_shipped").contains(order.getStatus())) {
            throw new BusinessException("只有已审核的销售单才能发货，当前状态: " + order.getStatus());
        }
        List<OrderRequests.OrderItem> items = body.items() == null ? List.of() : body.items();
        if (items.isEmpty()) {
            throw new BusinessException("发货明细不能为空");
        }
        Map<Long, SoOrderItem> itemMap = new HashMap<>();
        for (SoOrderItem it : order.getItems()) itemMap.put(it.getProductId(), it);
        for (OrderRequests.OrderItem b : items) {
            BigDecimal qty = Validators.requireIntQty(b.qty(), b.productId(), "发货数量");
            BigDecimal price = b.price();
            if (price == null || price.signum() < 0) {
                throw new BusinessException("发货单价不能为负");
            }
            SoOrderItem soItem = itemMap.get(b.productId());
            if (soItem == null) {
                throw new BusinessException("商品 #" + b.productId() + " 不在销售单中");
            }
            BigDecimal remain = soItem.getQty().subtract(soItem.getShippedQty());
            if (qty.compareTo(remain) > 0) {
                throw new BusinessException("商品「" + soItem.getProduct().getName()
                        + "」发货数量 " + qty.stripTrailingZeros().toPlainString()
                        + " 超过未发数量 " + remain.stripTrailingZeros().toPlainString());
            }
            BigDecimal stockQty = inventoryService.getStockQty(b.productId(), order.getWarehouseId());
            if (qty.compareTo(stockQty) > 0) {
                throw new BusinessException("商品「" + soItem.getProduct().getName() + "」库存不足：当前 "
                        + stockQty.stripTrailingZeros().toPlainString() + "，需要 "
                        + qty.stripTrailingZeros().toPlainString());
            }
        }

        SoStockOut stockOut = new SoStockOut();
        stockOut.setStockOutNo(billNoGenerator.gen("stock_out"));
        stockOut.setSoId(order.getId());
        stockOut.setSoNo(order.getOrderNo());
        stockOut.setCustomerId(order.getCustomerId());
        stockOut.setWarehouseId(order.getWarehouseId());
        stockOut.setRemark(body.remark());
        stockOut.setCreatedBy(username);
        BigDecimal total = BigDecimal.ZERO;
        for (OrderRequests.OrderItem b : items) {
            BigDecimal qty = Validators.requireIntQty(b.qty(), b.productId(), "发货数量");
            SoOrderItem soItem = itemMap.get(b.productId());
            BigDecimal price = b.price();
            BigDecimal amount = qty.multiply(price);
            total = total.add(amount);
            soItem.setShippedQty(soItem.getShippedQty().add(qty));
            SoStockOutItem soItemOut = new SoStockOutItem();
            soItemOut.setProductId(b.productId());
            soItemOut.setQty(qty);
            soItemOut.setPrice(price);
            soItemOut.setAmount(amount);
            soItemOut.setStockOut(stockOut);
            stockOut.getItems().add(soItemOut);
            inventoryService.changeStock(b.productId(), order.getWarehouseId(), qty.negate(),
                    "sale_out", stockOut.getStockOutNo(), username, "销售出库 " + order.getOrderNo());
        }
        stockOut.setTotalAmount(total);
        stockOutRepository.save(stockOut);

        FinReceivable receivable = new FinReceivable();
        receivable.setReceivableNo(billNoGenerator.gen("receivable"));
        receivable.setSourceNo(stockOut.getStockOutNo());
        receivable.setCustomerId(order.getCustomerId());
        receivable.setTotalAmount(total);
        receivable.setDueDate(LocalDate.now());
        receivable.setRemark("销售出库 " + order.getOrderNo());
        receivable.setCreatedBy(username);
        receivableRepository.save(receivable);

        boolean allShipped = order.getItems().stream()
                .allMatch(it -> it.getShippedQty().compareTo(it.getQty()) >= 0);
        order.setStatus(allShipped ? "completed" : "partially_shipped");
        orderRepository.save(order);
        return stockOut;
    }

    @Transactional
    public void deleteOrder(Long id, String username, String ip) {
        SoOrder order = getOrder(id);
        if (!"draft".equals(order.getStatus())) {
            throw new BusinessException("仅草稿状态可删除");
        }
        orderRepository.delete(order);
        auditService.write(username, "delete", "sales", order.getOrderNo(), null, ip);
    }

    @Transactional(readOnly = true)
    public SoOrder getOrder(Long id) {
        return orderRepository.findWithItemsById(id)
                .orElseThrow(() -> new BusinessException("销售单不存在"));
    }

    @Transactional(readOnly = true)
    public PageResult pageOrders(String status, String keyword, int pageNo, int pageSize) {
        Page<SoOrder> p = orderRepository.search(status, keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::soOrder).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> orderDetail(Long id) {
        SoOrder order = getOrder(id);
        Map<String, Object> data = Rows.soOrder(order);
        data.put("items", order.getItems().stream().map(Rows::soItem).toList());
        return data;
    }

    @Transactional(readOnly = true)
    public PageResult pageStockOuts(String keyword, int pageNo, int pageSize) {
        Page<SoStockOut> p = stockOutRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::soStockOut).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> stockOutDetail(Long id) {
        SoStockOut so = stockOutRepository.findById(id)
                .orElseThrow(() -> new BusinessException("出库单不存在"));
        Map<String, Object> data = Rows.soStockOut(so);
        data.put("items", so.getItems().stream().map(Rows::soStockOutItem).toList());
        return data;
    }

    private static String statusText(String status) {
        return switch (status) {
            case "draft" -> "草稿";
            case "approved" -> "已审核";
            case "partially_shipped" -> "部分发货";
            case "completed" -> "已完成";
            case "cancelled" -> "已取消";
            default -> status;
        };
    }
}
