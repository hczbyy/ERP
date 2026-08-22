package com.openerp.controller;

import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.common.RequirePermission;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.InventoryRequests;
import com.openerp.service.InventoryService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/inventory")
public class InventoryController {
    private final InventoryService inventoryService;

    public InventoryController(InventoryService inventoryService) {
        this.inventoryService = inventoryService;
    }

    private AuthUser user(HttpServletRequest request) {
        return SecurityInterceptor.current(request);
    }

    @GetMapping("/stocks")
    @RequirePermission("inventory:stock:read")
    public ApiResponse listStocks(@RequestParam(defaultValue = "") String keyword,
                                  @RequestParam(required = false) Long warehouseId,
                                  @RequestParam(defaultValue = "false") boolean lowStockOnly,
                                  @RequestParam(defaultValue = "1") int page,
                                  @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(inventoryService.pageStocks(keyword, warehouseId, lowStockOnly, page, pageSize));
    }

    @GetMapping("/logs")
    @RequirePermission("inventory:stock:read")
    public ApiResponse listLogs(@RequestParam(required = false) Long productId,
                                @RequestParam(required = false) Long warehouseId,
                                @RequestParam(defaultValue = "") String logType,
                                @RequestParam(defaultValue = "1") int page,
                                @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(inventoryService.pageLogs(productId, warehouseId, logType, page, pageSize));
    }

    @GetMapping("/checks")
    @RequirePermission("inventory:manage")
    public ApiResponse listChecks(@RequestParam(defaultValue = "") String status,
                                  @RequestParam(defaultValue = "1") int page,
                                  @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(inventoryService.pageChecks(status, page, pageSize));
    }

    @GetMapping("/checks/{checkId}")
    @RequirePermission("inventory:manage")
    public ApiResponse checkDetail(@PathVariable Long checkId) {
        return ApiResponse.ok(inventoryService.checkDetail(checkId));
    }

    @PostMapping("/checks")
    @RequirePermission("inventory:manage")
    public ApiResponse createCheck(@Valid @RequestBody InventoryRequests.CheckCreateBody body,
                                   HttpServletRequest request) {
        return ApiResponse.ok(inventoryService.createCheck(body, user(request).getUsername(),
                request.getRemoteAddr()), "盘点单创建成功");
    }

    @PutMapping("/checks/{checkId}")
    @RequirePermission("inventory:manage")
    public ApiResponse updateCheck(@PathVariable Long checkId,
                                   @Valid @RequestBody InventoryRequests.CheckUpdateBody body,
                                   HttpServletRequest request) {
        return ApiResponse.ok(inventoryService.updateCheck(checkId, body, user(request).getUsername(),
                request.getRemoteAddr()), "实盘数量已保存");
    }

    @PostMapping("/checks/{checkId}/done")
    @RequirePermission("inventory:manage")
    public ApiResponse doneCheck(@PathVariable Long checkId, HttpServletRequest request) {
        inventoryService.doneCheck(checkId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("盘点完成，库存已调整");
    }

    @GetMapping("/transfers")
    @RequirePermission("inventory:manage")
    public ApiResponse listTransfers(@RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(inventoryService.pageTransfers(page, pageSize));
    }

    @PostMapping("/transfers")
    @RequirePermission("inventory:manage")
    public ApiResponse createTransfer(@Valid @RequestBody InventoryRequests.TransferBody body,
                                      HttpServletRequest request) {
        return ApiResponse.ok(inventoryService.createTransfer(body, user(request).getUsername(),
                request.getRemoteAddr()), "调拨成功");
    }
}
