package com.openerp.controller;

import com.openerp.audit.AuditService;
import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.common.RequirePermission;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.OrderRequests;
import com.openerp.entity.PoOrder;
import com.openerp.entity.PoStockIn;
import com.openerp.service.PurchaseService;
import com.openerp.util.Rows;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/purchase")
public class PurchaseController {
    private final PurchaseService purchaseService;
    private final AuditService auditService;

    public PurchaseController(PurchaseService purchaseService, AuditService auditService) {
        this.purchaseService = purchaseService;
        this.auditService = auditService;
    }

    private AuthUser user(HttpServletRequest request) {
        return SecurityInterceptor.current(request);
    }

    @GetMapping("/orders")
    @RequirePermission("purchase:order:read")
    public ApiResponse listOrders(@RequestParam(defaultValue = "") String status,
                                  @RequestParam(defaultValue = "") String keyword,
                                  @RequestParam(defaultValue = "1") int page,
                                  @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(purchaseService.pageOrders(status, keyword, page, pageSize));
    }

    @GetMapping("/orders/{orderId}")
    @RequirePermission("purchase:order:read")
    public ApiResponse orderDetail(@PathVariable Long orderId) {
        return ApiResponse.ok(purchaseService.orderDetail(orderId));
    }

    @PostMapping("/orders")
    @RequirePermission("purchase:order:manage")
    public ApiResponse createOrder(@Valid @RequestBody OrderRequests.PurchaseOrderBody body,
                                   HttpServletRequest request) {
        PoOrder o = purchaseService.createOrder(body, user(request).getUsername());
        auditService.write(user(request).getUsername(), "create", "purchase", o.getOrderNo(),
                Map.of("supplier_id", body.supplierId(), "amount", o.getTotalAmount().toPlainString()),
                request.getRemoteAddr());
        return ApiResponse.ok(Rows.poOrder(o), "采购单创建成功");
    }

    @PutMapping("/orders/{orderId}")
    @RequirePermission("purchase:order:manage")
    public ApiResponse updateOrder(@PathVariable Long orderId,
                                   @Valid @RequestBody OrderRequests.PurchaseOrderBody body,
                                   HttpServletRequest request) {
        PoOrder o = purchaseService.updateOrder(orderId, body, user(request).getUsername());
        auditService.write(user(request).getUsername(), "update", "purchase", o.getOrderNo(),
                null, request.getRemoteAddr());
        return ApiResponse.ok(Rows.poOrder(o), "采购单已更新");
    }

    @PostMapping("/orders/{orderId}/approve")
    @RequirePermission("purchase:order:manage")
    public ApiResponse approveOrder(@PathVariable Long orderId, HttpServletRequest request) {
        PoOrder o = purchaseService.approveOrder(orderId, user(request).getUsername());
        auditService.write(user(request).getUsername(), "approve", "purchase", o.getOrderNo(),
                null, request.getRemoteAddr());
        return ApiResponse.ok(Rows.poOrder(o), "审核成功");
    }

    @PostMapping("/orders/{orderId}/cancel")
    @RequirePermission("purchase:order:manage")
    public ApiResponse cancelOrder(@PathVariable Long orderId,
                                   @RequestBody(required = false) OrderRequests.CancelBody body,
                                   HttpServletRequest request) {
        String reason = body == null ? null : body.reason();
        PoOrder o = purchaseService.cancelOrder(orderId, reason, user(request).getUsername());
        auditService.write(user(request).getUsername(), "cancel", "purchase", o.getOrderNo(),
                null, request.getRemoteAddr());
        return ApiResponse.ok(Rows.poOrder(o), "已取消");
    }

    @PostMapping("/orders/{orderId}/receive")
    @RequirePermission("purchase:receive:manage")
    public ApiResponse receiveOrder(@PathVariable Long orderId,
                                    @Valid @RequestBody OrderRequests.ReceiveShipBody body,
                                    HttpServletRequest request) {
        PoStockIn si = purchaseService.receiveOrder(orderId, body, user(request).getUsername());
        auditService.write(user(request).getUsername(), "receive", "purchase", si.getStockInNo(),
                Map.of("po_no", si.getPoNo(), "amount", si.getTotalAmount().toPlainString()),
                request.getRemoteAddr());
        return ApiResponse.ok(Map.of("stock_in_no", si.getStockInNo(), "total_amount", si.getTotalAmount()),
                "收货入库成功");
    }

    @DeleteMapping("/orders/{orderId}")
    @RequirePermission("purchase:order:manage")
    public ApiResponse deleteOrder(@PathVariable Long orderId, HttpServletRequest request) {
        purchaseService.deleteOrder(orderId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("采购单已删除");
    }

    @GetMapping("/stock-ins")
    @RequirePermission("purchase:order:read")
    public ApiResponse listStockIns(@RequestParam(defaultValue = "") String keyword,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(purchaseService.pageStockIns(keyword, page, pageSize));
    }

    @GetMapping("/stock-ins/{siId}")
    @RequirePermission("purchase:order:read")
    public ApiResponse stockInDetail(@PathVariable Long siId) {
        return ApiResponse.ok(purchaseService.stockInDetail(siId));
    }
}
