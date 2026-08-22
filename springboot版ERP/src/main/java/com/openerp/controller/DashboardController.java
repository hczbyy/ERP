package com.openerp.controller;

import com.openerp.common.ApiResponse;
import com.openerp.common.RequirePermission;
import com.openerp.service.DashboardService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/dashboard")
public class DashboardController {
    private final DashboardService dashboardService;

    public DashboardController(DashboardService dashboardService) {
        this.dashboardService = dashboardService;
    }

    @GetMapping("/summary")
    @RequirePermission("dashboard:view")
    public ApiResponse summary() {
        return ApiResponse.ok(dashboardService.summary());
    }

    @GetMapping("/sales-trend")
    @RequirePermission("dashboard:view")
    public ApiResponse salesTrend(@RequestParam(defaultValue = "7") int days) {
        return ApiResponse.ok(dashboardService.salesTrend(days));
    }

    @GetMapping("/top-products")
    @RequirePermission("dashboard:view")
    public ApiResponse topProducts(@RequestParam(defaultValue = "5") int limit) {
        return ApiResponse.ok(dashboardService.topProducts(limit));
    }

    @GetMapping("/low-stocks")
    @RequirePermission("dashboard:view")
    public ApiResponse lowStocks(@RequestParam(defaultValue = "10") int limit) {
        return ApiResponse.ok(dashboardService.lowStocks(limit));
    }

    @GetMapping("/recent-orders")
    @RequirePermission("dashboard:view")
    public ApiResponse recentOrders(@RequestParam(defaultValue = "8") int limit) {
        return ApiResponse.ok(dashboardService.recentOrders(limit));
    }
}
