package com.openerp.service;

import com.openerp.audit.AuditService;
import com.openerp.common.BusinessException;
import com.openerp.common.PageResult;
import com.openerp.dto.InventoryRequests;
import com.openerp.entity.*;
import com.openerp.repository.*;
import com.openerp.util.BillNoGenerator;
import com.openerp.util.Rows;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

@Service
public class InventoryService {
    private final InvStockRepository stockRepository;
    private final InvStockLogRepository logRepository;
    private final InvStockCheckRepository checkRepository;
    private final InvStockTransferRepository transferRepository;
    private final MdProductRepository productRepository;
    private final MdWarehouseRepository warehouseRepository;
    private final AuditService auditService;
    private final BillNoGenerator billNoGenerator;

    public InventoryService(InvStockRepository stockRepository,
                            InvStockLogRepository logRepository,
                            InvStockCheckRepository checkRepository,
                            InvStockTransferRepository transferRepository,
                            MdProductRepository productRepository,
                            MdWarehouseRepository warehouseRepository,
                            AuditService auditService,
                            BillNoGenerator billNoGenerator) {
        this.stockRepository = stockRepository;
        this.logRepository = logRepository;
        this.checkRepository = checkRepository;
        this.transferRepository = transferRepository;
        this.productRepository = productRepository;
        this.warehouseRepository = warehouseRepository;
        this.auditService = auditService;
        this.billNoGenerator = billNoGenerator;
    }

    // ---------------- 库存变动核心 ----------------

    @Transactional
    public InvStock changeStock(Long productId, Long warehouseId, BigDecimal delta,
                                String logType, String refNo, String createdBy, String remark) {
        delta = delta.setScale(2);
        InvStock stock = stockRepository.findByProductIdAndWarehouseId(productId, warehouseId)
                .orElse(null);
        if (stock == null) {
            if (delta.signum() < 0) {
                throw new BusinessException("该商品在此仓库没有库存，无法出库");
            }
            stock = new InvStock();
            stock.setProductId(productId);
            stock.setWarehouseId(warehouseId);
            stock.setQty(BigDecimal.ZERO);
            stockRepository.save(stock);
        }
        BigDecimal before = stock.getQty();
        BigDecimal after = before.add(delta);
        if (after.signum() < 0) {
            throw new BusinessException(String.format(
                    "库存不足：商品#%d 当前 %s，本次需要 %s", productId, before.stripTrailingZeros().toPlainString(),
                    delta.abs().stripTrailingZeros().toPlainString()));
        }
        stock.setQty(after);
        stockRepository.save(stock);

        InvStockLog log = new InvStockLog();
        log.setProductId(productId);
        log.setWarehouseId(warehouseId);
        log.setChangeQty(delta);
        log.setBeforeQty(before);
        log.setAfterQty(after);
        log.setLogType(logType);
        log.setRefNo(refNo);
        log.setRemark(remark);
        log.setCreatedBy(createdBy);
        log.setCreatedAt(LocalDateTime.now());
        logRepository.save(log);
        return stock;
    }

    public BigDecimal getStockQty(Long productId, Long warehouseId) {
        return stockRepository.findByProductIdAndWarehouseId(productId, warehouseId)
                .map(InvStock::getQty).orElse(BigDecimal.ZERO);
    }

    // ---------------- 库存查询 ----------------

    @Transactional(readOnly = true)
    public PageResult pageStocks(String keyword, Long warehouseId, boolean lowStockOnly,
                                 int pageNo, int pageSize) {
        Page<Object[]> p = stockRepository.searchStocks(warehouseId, keyword, lowStockOnly,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        Map<Long, String> whNames = new HashMap<>();
        for (MdWarehouse w : warehouseRepository.findAll()) whNames.put(w.getId(), w.getName());
        List<Map<String, Object>> items = new ArrayList<>();
        for (Object[] row : p.getContent()) {
            InvStock s = (InvStock) row[0];
            MdProduct prod = (MdProduct) row[1];
            items.add(Rows.stock(s, prod, whNames.get(s.getWarehouseId())));
        }
        return new PageResult(items, p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public PageResult pageLogs(Long productId, Long warehouseId, String logType,
                               int pageNo, int pageSize) {
        Page<InvStockLog> p = logRepository.search(productId, warehouseId, logType,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        Map<Long, String> whNames = new HashMap<>();
        for (MdWarehouse w : warehouseRepository.findAll()) whNames.put(w.getId(), w.getName());
        List<Map<String, Object>> items = p.getContent().stream()
                .map(l -> Rows.stockLog(l, l.getProduct(), whNames.get(l.getWarehouseId())))
                .toList();
        return new PageResult(items, p.getTotalElements(), pageNo, pageSize);
    }

    // ---------------- 盘点 ----------------

    @Transactional(readOnly = true)
    public PageResult pageChecks(String status, int pageNo, int pageSize) {
        Page<InvStockCheck> p = checkRepository.search(status,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(c -> Rows.check(c, null)).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> checkDetail(Long id) {
        InvStockCheck c = checkRepository.findWithItemsById(id)
                .orElseThrow(() -> new BusinessException("盘点单不存在"));
        Map<Long, MdProduct> products = productMap();
        List<Map<String, Object>> items = c.getItems().stream()
                .map(it -> Rows.checkItem(it, products.get(it.getProductId()))).toList();
        return Rows.check(c, items);
    }

    @Transactional
    public Map<String, Object> createCheck(InventoryRequests.CheckCreateBody body,
                                           String username, String ip) {
        if (!warehouseRepository.existsById(body.warehouseId())) {
            throw new BusinessException("仓库不存在");
        }
        List<Long> ids = new ArrayList<>(new LinkedHashSet<>(body.productIds()));
        Set<Long> found = new HashSet<>();
        for (MdProduct p : productRepository.findAllById(ids)) found.add(p.getId());
        List<Long> missing = ids.stream().filter(i -> !found.contains(i)).toList();
        if (!missing.isEmpty()) {
            throw new BusinessException("商品不存在: " + missing);
        }
        InvStockCheck c = new InvStockCheck();
        c.setCheckNo(billNoGenerator.gen("stock_check"));
        c.setWarehouseId(body.warehouseId());
        c.setRemark(body.remark());
        c.setCreatedBy(username);
        for (Long pid : ids) {
            BigDecimal book = stockRepository.findByProductIdAndWarehouseId(pid, body.warehouseId())
                    .map(InvStock::getQty).orElse(BigDecimal.ZERO);
            InvStockCheckItem item = new InvStockCheckItem();
            item.setProductId(pid);
            item.setBookQty(book);
            item.setCheck(c);
            c.getItems().add(item);
        }
        checkRepository.save(c);
        auditService.write(username, "create", "inventory", c.getCheckNo(), null, ip);
        return checkDetail(c.getId());
    }

    @Transactional
    public Map<String, Object> updateCheck(Long id, InventoryRequests.CheckUpdateBody body,
                                           String username, String ip) {
        InvStockCheck c = checkRepository.findWithItemsById(id)
                .orElseThrow(() -> new BusinessException("盘点单不存在"));
        if (!"draft".equals(c.getStatus())) {
            throw new BusinessException("仅草稿状态可录入实盘数量");
        }
        Map<Long, InvStockCheckItem> itemMap = new HashMap<>();
        for (InvStockCheckItem it : c.getItems()) itemMap.put(it.getProductId(), it);
        for (InventoryRequests.CheckItemBody b : body.items()) {
            InvStockCheckItem item = itemMap.get(b.productId());
            if (item == null) {
                throw new BusinessException("商品 #" + b.productId() + " 不在盘点单中");
            }
            item.setActualQty(BigDecimal.valueOf(b.actualQty()));
            item.setDiffQty(item.getActualQty().subtract(item.getBookQty()));
        }
        checkRepository.save(c);
        auditService.write(username, "update", "inventory", c.getCheckNo(), null, ip);
        return checkDetail(c.getId());
    }

    @Transactional
    public void doneCheck(Long id, String username, String ip) {
        InvStockCheck c = checkRepository.findWithItemsById(id)
                .orElseThrow(() -> new BusinessException("盘点单不存在"));
        if (!"draft".equals(c.getStatus())) {
            throw new BusinessException("盘点单已提交");
        }
        for (InvStockCheckItem it : c.getItems()) {
            BigDecimal diff = it.getActualQty().subtract(it.getBookQty());
            if (diff.signum() == 0) continue;
            changeStock(it.getProductId(), c.getWarehouseId(), diff,
                    diff.signum() > 0 ? "check_in" : "check_out",
                    c.getCheckNo(), username, "盘点调整(" + c.getCheckNo() + ")");
        }
        c.setStatus("done");
        c.setDoneBy(username);
        c.setDoneAt(LocalDateTime.now());
        checkRepository.save(c);
        auditService.write(username, "check", "inventory", c.getCheckNo(), null, ip);
    }

    // ---------------- 调拨 ----------------

    @Transactional(readOnly = true)
    public PageResult pageTransfers(int pageNo, int pageSize) {
        Page<InvStockTransfer> p = transferRepository.findAllWithWarehouses(
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::transfer).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createTransfer(InventoryRequests.TransferBody body,
                                              String username, String ip) {
        if (body.fromWarehouseId().equals(body.toWarehouseId())) {
            throw new BusinessException("调出与调入仓库不能相同");
        }
        if (!warehouseRepository.existsById(body.fromWarehouseId())) {
            throw new BusinessException("调出仓库不存在");
        }
        if (!warehouseRepository.existsById(body.toWarehouseId())) {
            throw new BusinessException("调入仓库不存在");
        }
        Set<Long> found = new HashSet<>();
        for (MdProduct p : productRepository.findAllById(
                body.items().stream().map(InventoryRequests.TransferItemBody::productId).toList())) {
            found.add(p.getId());
        }
        List<Long> missing = body.items().stream()
                .map(InventoryRequests.TransferItemBody::productId)
                .filter(i -> !found.contains(i)).toList();
        if (!missing.isEmpty()) {
            throw new BusinessException("商品不存在: " + missing);
        }
        InvStockTransfer t = new InvStockTransfer();
        t.setTransferNo(billNoGenerator.gen("stock_transfer"));
        t.setFromWarehouseId(body.fromWarehouseId());
        t.setToWarehouseId(body.toWarehouseId());
        t.setRemark(body.remark());
        t.setCreatedBy(username);
        transferRepository.save(t);
        for (InventoryRequests.TransferItemBody it : body.items()) {
            BigDecimal qty = BigDecimal.valueOf(it.qty());
            changeStock(it.productId(), body.fromWarehouseId(), qty.negate(), "transfer_out",
                    t.getTransferNo(), username, "调拨至仓#" + body.toWarehouseId());
            changeStock(it.productId(), body.toWarehouseId(), qty, "transfer_in",
                    t.getTransferNo(), username, "自仓#" + body.fromWarehouseId() + "调入");
            InvStockTransferItem ti = new InvStockTransferItem();
            ti.setProductId(it.productId());
            ti.setQty(qty);
            ti.setTransfer(t);
            t.getItems().add(ti);
        }
        transferRepository.save(t);
        auditService.write(username, "transfer", "inventory", t.getTransferNo(), null, ip);
        return Rows.transfer(t);
    }

    private Map<Long, MdProduct> productMap() {
        Map<Long, MdProduct> map = new HashMap<>();
        for (MdProduct p : productRepository.findAll()) map.put(p.getId(), p);
        return map;
    }
}
