package com.openerp.controller;

import com.openerp.audit.AuditService;
import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.common.RequirePermission;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.OrderRequests;
import com.openerp.entity.SoOrder;
import com.openerp.entity.SoStockOut;
import com.openerp.service.SalesService;
import com.openerp.util.Rows;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api/sales")
public class SalesController {
    private final SalesService salesService;
    private final AuditService auditService;

    public SalesController(SalesService salesService, AuditService auditService) {
        this.salesService = salesService;
        this.auditService = auditService;
    }

    private AuthUser user(HttpServletRequest request) {
        return SecurityInterceptor.current(request);
    }

    @GetMapping("/orders")
    @RequirePermission("sales:order:read")
    public ApiResponse listOrders(@RequestParam(defaultValue = "") String status,
                                  @RequestParam(defaultValue = "") String keyword,
                                  @RequestParam(defaultValue = "1") int page,
                                  @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(salesService.pageOrders(status, keyword, page, pageSize));
    }

    @GetMapping("/orders/{orderId}")
    @RequirePermission("sales:order:read")
    public ApiResponse orderDetail(@PathVariable Long orderId) {
        return ApiResponse.ok(salesService.orderDetail(orderId));
    }

    @PostMapping("/orders")
    @RequirePermission("sales:order:manage")
    public ApiResponse createOrder(@Valid @RequestBody OrderRequests.SalesOrderBody body,
                                   HttpServletRequest request) {
        SoOrder o = salesService.createOrder(body, user(request).getUsername());
        auditService.write(user(request).getUsername(), "create", "sales", o.getOrderNo(),
                Map.of("customer_id", body.customerId(), "amount", o.getTotalAmount().toPlainString()),
                request.getRemoteAddr());
        return ApiResponse.ok(Rows.soOrder(o), "销售单创建成功");
    }

    @PutMapping("/orders/{orderId}")
    @RequirePermission("sales:order:manage")
    public ApiResponse updateOrder(@PathVariable Long orderId,
                                   @Valid @RequestBody OrderRequests.SalesOrderBody body,
                                   HttpServletRequest request) {
        SoOrder o = salesService.updateOrder(orderId, body, user(request).getUsername());
        auditService.write(user(request).getUsername(), "update", "sales", o.getOrderNo(),
                null, request.getRemoteAddr());
        return ApiResponse.ok(Rows.soOrder(o), "销售单已更新");
    }

    @PostMapping("/orders/{orderId}/approve")
    @RequirePermission("sales:order:manage")
    public ApiResponse approveOrder(@PathVariable Long orderId, HttpServletRequest request) {
        SoOrder o = salesService.approveOrder(orderId, user(request).getUsername());
        auditService.write(user(request).getUsername(), "approve", "sales", o.getOrderNo(),
                null, request.getRemoteAddr());
        return ApiResponse.ok(Rows.soOrder(o), "审核成功");
    }

    @PostMapping("/orders/{orderId}/cancel")
    @RequirePermission("sales:order:manage")
    public ApiResponse cancelOrder(@PathVariable Long orderId,
                                   @RequestBody(required = false) OrderRequests.CancelBody body,
                                   HttpServletRequest request) {
        String reason = body == null ? null : body.reason();
        SoOrder o = salesService.cancelOrder(orderId, reason, user(request).getUsername());
        auditService.write(user(request).getUsername(), "cancel", "sales", o.getOrderNo(),
                null, request.getRemoteAddr());
        return ApiResponse.ok(Rows.soOrder(o), "已取消");
    }

    @PostMapping("/orders/{orderId}/ship")
    @RequirePermission("sales:ship:manage")
    public ApiResponse shipOrder(@PathVariable Long orderId,
                                 @Valid @RequestBody OrderRequests.ReceiveShipBody body,
                                 HttpServletRequest request) {
        SoStockOut so = salesService.shipOrder(orderId, body, user(request).getUsername());
        auditService.write(user(request).getUsername(), "ship", "sales", so.getStockOutNo(),
                Map.of("so_no", so.getSoNo(), "amount", so.getTotalAmount().toPlainString()),
                request.getRemoteAddr());
        return ApiResponse.ok(Map.of("stock_out_no", so.getStockOutNo(), "total_amount", so.getTotalAmount()),
                "发货成功");
    }

    @DeleteMapping("/orders/{orderId}")
    @RequirePermission("sales:order:manage")
    public ApiResponse deleteOrder(@PathVariable Long orderId, HttpServletRequest request) {
        salesService.deleteOrder(orderId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("销售单已删除");
    }

    @GetMapping("/stock-outs")
    @RequirePermission("sales:order:read")
    public ApiResponse listStockOuts(@RequestParam(defaultValue = "") String keyword,
                                     @RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(salesService.pageStockOuts(keyword, page, pageSize));
    }

    @GetMapping("/stock-outs/{soId}")
    @RequirePermission("sales:order:read")
    public ApiResponse stockOutDetail(@PathVariable Long soId) {
        return ApiResponse.ok(salesService.stockOutDetail(soId));
    }
}
