package com.openerp.controller;

import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.common.RequirePermission;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.FinanceRequests;
import com.openerp.service.FinanceService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/finance")
public class FinanceController {
    private final FinanceService financeService;

    public FinanceController(FinanceService financeService) {
        this.financeService = financeService;
    }

    private AuthUser user(HttpServletRequest request) {
        return SecurityInterceptor.current(request);
    }

    @GetMapping("/receivables")
    @RequirePermission("finance:read")
    public ApiResponse listReceivables(@RequestParam(defaultValue = "") String status,
                                       @RequestParam(defaultValue = "") String keyword,
                                       @RequestParam(defaultValue = "1") int page,
                                       @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(financeService.pageReceivables(status, keyword, page, pageSize));
    }

    @PostMapping("/receivables")
    @RequirePermission("finance:manage")
    public ApiResponse createReceivable(@Valid @RequestBody FinanceRequests.ReceivableCreateBody body,
                                        HttpServletRequest request) {
        return ApiResponse.ok(financeService.createReceivable(body, user(request).getUsername(),
                request.getRemoteAddr()), "应收单创建成功");
    }

    @GetMapping("/payables")
    @RequirePermission("finance:read")
    public ApiResponse listPayables(@RequestParam(defaultValue = "") String status,
                                    @RequestParam(defaultValue = "") String keyword,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(financeService.pagePayables(status, keyword, page, pageSize));
    }

    @PostMapping("/payables")
    @RequirePermission("finance:manage")
    public ApiResponse createPayable(@Valid @RequestBody FinanceRequests.PayableCreateBody body,
                                     HttpServletRequest request) {
        return ApiResponse.ok(financeService.createPayable(body, user(request).getUsername(),
                request.getRemoteAddr()), "应付单创建成功");
    }

    @GetMapping("/receipts")
    @RequirePermission("finance:read")
    public ApiResponse listReceipts(@RequestParam(defaultValue = "") String keyword,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(financeService.pageReceipts(keyword, page, pageSize));
    }

    @PostMapping("/receipts")
    @RequirePermission("finance:manage")
    public ApiResponse createReceipt(@Valid @RequestBody FinanceRequests.ReceiptBody body,
                                     HttpServletRequest request) {
        return ApiResponse.ok(financeService.createReceipt(body, user(request).getUsername(),
                request.getRemoteAddr()), "收款登记成功");
    }

    @GetMapping("/payments")
    @RequirePermission("finance:read")
    public ApiResponse listPayments(@RequestParam(defaultValue = "") String keyword,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(financeService.pagePayments(keyword, page, pageSize));
    }

    @PostMapping("/payments")
    @RequirePermission("finance:manage")
    public ApiResponse createPayment(@Valid @RequestBody FinanceRequests.PaymentBody body,
                                     HttpServletRequest request) {
        return ApiResponse.ok(financeService.createPayment(body, user(request).getUsername(),
                request.getRemoteAddr()), "付款登记成功");
    }
}
