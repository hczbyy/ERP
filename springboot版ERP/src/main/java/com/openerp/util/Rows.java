package com.openerp.util;

import com.openerp.entity.*;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class Rows {
    private static final Map<String, String> PO_STATUS = Map.of(
            "draft", "草稿", "approved", "已审核", "partially_received", "部分收货",
            "completed", "已完成", "cancelled", "已取消");
    private static final Map<String, String> SO_STATUS = Map.of(
            "draft", "草稿", "approved", "已审核", "partially_shipped", "部分发货",
            "completed", "已完成", "cancelled", "已取消");
    private static final Map<String, String> FIN_STATUS = Map.of(
            "open", "未核销", "partial", "部分核销", "settled", "已核销");
    private static final Map<String, String> LOG_TYPE = Map.of(
            "purchase_in", "采购入库", "sale_out", "销售出库", "transfer_in", "调拨入库",
            "transfer_out", "调拨出库", "check_in", "盘盈调整", "check_out", "盘亏调整", "initial", "期初建账");

    private Rows() {
    }

    public static Map<String, Object> map(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    public static Map<String, Object> user(SysUser u) {
        Map<String, Object> m = map(
                "id", u.getId(), "username", u.getUsername(), "display_name", u.getDisplayName(),
                "email", u.getEmail(), "phone", u.getPhone(), "is_active", u.isActive(),
                "is_superuser", u.isSuperuser(), "created_at", u.getCreatedAt());
        m.put("roles", u.getRoles().stream().map(r -> map("id", r.getId(), "code", r.getCode(), "name", r.getName())).toList());
        return m;
    }

    public static Map<String, Object> role(SysRole r) {
        Map<String, Object> m = map(
                "id", r.getId(), "code", r.getCode(), "name", r.getName(),
                "description", r.getDescription(), "is_builtin", r.isBuiltin());
        m.put("permission_ids", r.getPermissions().stream().map(SysPermission::getId).toList());
        return m;
    }

    public static Map<String, Object> category(MdCategory c) {
        return map("id", c.getId(), "name", c.getName(), "sort", c.getSort());
    }

    public static Map<String, Object> product(MdProduct p) {
        return map(
                "id", p.getId(), "code", p.getCode(), "name", p.getName(), "spec", p.getSpec(),
                "unit", p.getUnit(), "barcode", p.getBarcode(), "category_id", p.getCategoryId(),
                "category_name", p.getCategory() == null ? null : p.getCategory().getName(),
                "purchase_price", p.getPurchasePrice(), "sale_price", p.getSalePrice(),
                "safety_stock", p.getSafetyStock(), "status", p.getStatus(), "description", p.getDescription());
    }

    public static Map<String, Object> customer(MdCustomer c) {
        return map(
                "id", c.getId(), "code", c.getCode(), "name", c.getName(), "contact", c.getContact(),
                "phone", c.getPhone(), "address", c.getAddress(), "credit_limit", c.getCreditLimit(),
                "status", c.getStatus());
    }

    public static Map<String, Object> supplier(MdSupplier s) {
        return map(
                "id", s.getId(), "code", s.getCode(), "name", s.getName(), "contact", s.getContact(),
                "phone", s.getPhone(), "address", s.getAddress(), "status", s.getStatus());
    }

    public static Map<String, Object> warehouse(MdWarehouse w) {
        return map(
                "id", w.getId(), "code", w.getCode(), "name", w.getName(), "address", w.getAddress(),
                "manager", w.getManager(), "status", w.getStatus());
    }

    public static Map<String, Object> dept(OrgDepartment d) {
        return map("id", d.getId(), "code", d.getCode(), "name", d.getName(), "leader", d.getLeader(),
                "phone", d.getPhone(), "remark", d.getRemark());
    }

    public static Map<String, Object> emp(OrgEmployee e) {
        return map(
                "id", e.getId(), "emp_no", e.getEmpNo(), "name", e.getName(), "gender", e.getGender(),
                "phone", e.getPhone(), "email", e.getEmail(), "hire_date", e.getHireDate(),
                "position", e.getPosition(), "status", e.getStatus(), "department_id", e.getDepartmentId(),
                "department_name", e.getDepartment() == null ? null : e.getDepartment().getName());
    }

    public static Map<String, Object> poOrder(PoOrder o) {
        return map(
                "id", o.getId(), "order_no", o.getOrderNo(),
                "supplier_id", o.getSupplierId(),
                "supplier_name", o.getSupplier() == null ? null : o.getSupplier().getName(),
                "warehouse_id", o.getWarehouseId(),
                "warehouse_name", o.getWarehouse() == null ? null : o.getWarehouse().getName(),
                "status", o.getStatus(), "status_text", PO_STATUS.getOrDefault(o.getStatus(), o.getStatus()),
                "total_amount", o.getTotalAmount(), "remark", o.getRemark(),
                "approved_by", o.getApprovedBy(), "approved_at", o.getApprovedAt(),
                "created_by", o.getCreatedBy(), "cancel_reason", o.getCancelReason(),
                "created_at", o.getCreatedAt());
    }

    public static Map<String, Object> poItem(PoOrderItem it) {
        return map(
                "id", it.getId(), "product_id", it.getProductId(),
                "product_code", it.getProduct() == null ? null : it.getProduct().getCode(),
                "product_name", it.getProduct() == null ? null : it.getProduct().getName(),
                "unit", it.getProduct() == null ? null : it.getProduct().getUnit(),
                "qty", it.getQty(), "price", it.getPrice(), "amount", it.getAmount(),
                "received_qty", it.getReceivedQty(),
                "remain_qty", it.getQty().subtract(it.getReceivedQty()));
    }

    public static Map<String, Object> poStockIn(PoStockIn si) {
        return map(
                "id", si.getId(), "stock_in_no", si.getStockInNo(), "po_no", si.getPoNo(),
                "supplier_name", si.getSupplier() == null ? null : si.getSupplier().getName(),
                "warehouse_name", si.getWarehouse() == null ? null : si.getWarehouse().getName(),
                "total_amount", si.getTotalAmount(), "remark", si.getRemark(),
                "created_by", si.getCreatedBy(), "created_at", si.getCreatedAt());
    }

    public static Map<String, Object> poStockInItem(PoStockInItem it) {
        return map(
                "product_code", it.getProduct() == null ? null : it.getProduct().getCode(),
                "product_name", it.getProduct() == null ? null : it.getProduct().getName(),
                "qty", it.getQty(), "price", it.getPrice(), "amount", it.getAmount());
    }

    public static Map<String, Object> soOrder(SoOrder o) {
        return map(
                "id", o.getId(), "order_no", o.getOrderNo(),
                "customer_id", o.getCustomerId(),
                "customer_name", o.getCustomer() == null ? null : o.getCustomer().getName(),
                "warehouse_id", o.getWarehouseId(),
                "warehouse_name", o.getWarehouse() == null ? null : o.getWarehouse().getName(),
                "status", o.getStatus(), "status_text", SO_STATUS.getOrDefault(o.getStatus(), o.getStatus()),
                "total_amount", o.getTotalAmount(), "remark", o.getRemark(),
                "approved_by", o.getApprovedBy(), "approved_at", o.getApprovedAt(),
                "created_by", o.getCreatedBy(), "cancel_reason", o.getCancelReason(),
                "created_at", o.getCreatedAt());
    }

    public static Map<String, Object> soItem(SoOrderItem it) {
        return map(
                "id", it.getId(), "product_id", it.getProductId(),
                "product_code", it.getProduct() == null ? null : it.getProduct().getCode(),
                "product_name", it.getProduct() == null ? null : it.getProduct().getName(),
                "unit", it.getProduct() == null ? null : it.getProduct().getUnit(),
                "qty", it.getQty(), "price", it.getPrice(), "amount", it.getAmount(),
                "shipped_qty", it.getShippedQty(),
                "remain_qty", it.getQty().subtract(it.getShippedQty()));
    }

    public static Map<String, Object> soStockOut(SoStockOut so) {
        return map(
                "id", so.getId(), "stock_out_no", so.getStockOutNo(), "so_no", so.getSoNo(),
                "customer_name", so.getCustomer() == null ? null : so.getCustomer().getName(),
                "warehouse_name", so.getWarehouse() == null ? null : so.getWarehouse().getName(),
                "total_amount", so.getTotalAmount(), "remark", so.getRemark(),
                "created_by", so.getCreatedBy(), "created_at", so.getCreatedAt());
    }

    public static Map<String, Object> soStockOutItem(SoStockOutItem it) {
        return map(
                "product_code", it.getProduct() == null ? null : it.getProduct().getCode(),
                "product_name", it.getProduct() == null ? null : it.getProduct().getName(),
                "qty", it.getQty(), "price", it.getPrice(), "amount", it.getAmount());
    }

    public static Map<String, Object> stock(InvStock s, MdProduct p, String warehouseName) {
        return map(
                "id", s.getId(), "product_id", p.getId(), "product_code", p.getCode(),
                "product_name", p.getName(), "unit", p.getUnit(),
                "warehouse_id", s.getWarehouseId(), "warehouse_name", warehouseName,
                "qty", s.getQty(), "safety_stock", p.getSafetyStock(),
                "is_low", s.getQty().compareTo(p.getSafetyStock()) < 0);
    }

    public static Map<String, Object> stockLog(InvStockLog l, MdProduct p, String warehouseName) {
        return map(
                "id", l.getId(),
                "product_code", p == null ? null : p.getCode(),
                "product_name", p == null ? null : p.getName(),
                "warehouse_name", warehouseName,
                "change_qty", l.getChangeQty(), "before_qty", l.getBeforeQty(),
                "after_qty", l.getAfterQty(), "log_type", l.getLogType(),
                "log_type_text", LOG_TYPE.getOrDefault(l.getLogType(), l.getLogType()),
                "ref_no", l.getRefNo(), "remark", l.getRemark(),
                "created_by", l.getCreatedBy(), "created_at", l.getCreatedAt());
    }

    public static Map<String, Object> check(InvStockCheck c, List<Map<String, Object>> items) {
        Map<String, Object> m = map(
                "id", c.getId(), "check_no", c.getCheckNo(), "warehouse_id", c.getWarehouseId(),
                "warehouse_name", c.getWarehouse() == null ? null : c.getWarehouse().getName(),
                "status", c.getStatus(), "remark", c.getRemark(),
                "created_by", c.getCreatedBy(), "done_by", c.getDoneBy(), "done_at", c.getDoneAt(),
                "created_at", c.getCreatedAt());
        m.put("items", items);
        return m;
    }

    public static Map<String, Object> checkItem(InvStockCheckItem it, MdProduct p) {
        return map(
                "product_id", it.getProductId(),
                "product_code", p == null ? null : p.getCode(),
                "product_name", p == null ? null : p.getName(),
                "unit", p == null ? null : p.getUnit(),
                "book_qty", it.getBookQty(), "actual_qty", it.getActualQty(), "diff_qty", it.getDiffQty());
    }

    public static Map<String, Object> transfer(InvStockTransfer t) {
        return map(
                "id", t.getId(), "transfer_no", t.getTransferNo(),
                "from_warehouse_id", t.getFromWarehouseId(),
                "from_warehouse_name", t.getFromWarehouse() == null ? null : t.getFromWarehouse().getName(),
                "to_warehouse_id", t.getToWarehouseId(),
                "to_warehouse_name", t.getToWarehouse() == null ? null : t.getToWarehouse().getName(),
                "remark", t.getRemark(), "created_by", t.getCreatedBy(), "created_at", t.getCreatedAt());
    }

    public static Map<String, Object> receivable(FinReceivable r) {
        return map(
                "id", r.getId(), "receivable_no", r.getReceivableNo(), "source_no", r.getSourceNo(),
                "customer_id", r.getCustomerId(),
                "customer_name", r.getCustomer() == null ? null : r.getCustomer().getName(),
                "total_amount", r.getTotalAmount(), "received_amount", r.getReceivedAmount(),
                "balance", r.getTotalAmount().subtract(r.getReceivedAmount()),
                "status", r.getStatus(), "status_text", FIN_STATUS.getOrDefault(r.getStatus(), r.getStatus()),
                "due_date", r.getDueDate(), "remark", r.getRemark(),
                "created_by", r.getCreatedBy(), "created_at", r.getCreatedAt());
    }

    public static Map<String, Object> payable(FinPayable p) {
        return map(
                "id", p.getId(), "payable_no", p.getPayableNo(), "source_no", p.getSourceNo(),
                "supplier_id", p.getSupplierId(),
                "supplier_name", p.getSupplier() == null ? null : p.getSupplier().getName(),
                "total_amount", p.getTotalAmount(), "paid_amount", p.getPaidAmount(),
                "balance", p.getTotalAmount().subtract(p.getPaidAmount()),
                "status", p.getStatus(), "status_text", FIN_STATUS.getOrDefault(p.getStatus(), p.getStatus()),
                "due_date", p.getDueDate(), "remark", p.getRemark(),
                "created_by", p.getCreatedBy(), "created_at", p.getCreatedAt());
    }

    public static Map<String, Object> receipt(FinReceipt r) {
        return map(
                "id", r.getId(), "receipt_no", r.getReceiptNo(), "receivable_no", r.getReceivableNo(),
                "customer_name", r.getReceivable() == null || r.getReceivable().getCustomer() == null
                        ? null : r.getReceivable().getCustomer().getName(),
                "amount", r.getAmount(), "pay_method", r.getPayMethod(),
                "received_at", r.getReceivedAt(), "remark", r.getRemark(),
                "created_by", r.getCreatedBy(), "created_at", r.getCreatedAt());
    }

    public static Map<String, Object> payment(FinPayment p) {
        return map(
                "id", p.getId(), "payment_no", p.getPaymentNo(), "payable_no", p.getPayableNo(),
                "supplier_name", p.getPayable() == null || p.getPayable().getSupplier() == null
                        ? null : p.getPayable().getSupplier().getName(),
                "amount", p.getAmount(), "pay_method", p.getPayMethod(),
                "paid_at", p.getPaidAt(), "remark", p.getRemark(),
                "created_by", p.getCreatedBy(), "created_at", p.getCreatedAt());
    }
}
