package com.openerp.controller;

import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.common.RequirePermission;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.MasterRequests;
import com.openerp.service.MasterService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/master")
public class MasterController {
    private final MasterService masterService;

    public MasterController(MasterService masterService) {
        this.masterService = masterService;
    }

    private AuthUser user(HttpServletRequest request) {
        return SecurityInterceptor.current(request);
    }

    // ---------- 商品分类 ----------

    @GetMapping("/categories")
    @RequirePermission("master:product:read")
    public ApiResponse listCategories() {
        return ApiResponse.ok(masterService.listCategories());
    }

    @PostMapping("/categories")
    @RequirePermission("master:product:manage")
    public ApiResponse createCategory(@Valid @RequestBody MasterRequests.CategoryBody body,
                                      HttpServletRequest request) {
        return ApiResponse.ok(masterService.createCategory(body, user(request).getUsername(),
                request.getRemoteAddr()), "分类创建成功");
    }

    @PutMapping("/categories/{catId}")
    @RequirePermission("master:product:manage")
    public ApiResponse updateCategory(@PathVariable Long catId,
                                      @Valid @RequestBody MasterRequests.CategoryBody body,
                                      HttpServletRequest request) {
        masterService.updateCategory(catId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("分类更新成功");
    }

    @DeleteMapping("/categories/{catId}")
    @RequirePermission("master:product:manage")
    public ApiResponse deleteCategory(@PathVariable Long catId, HttpServletRequest request) {
        masterService.deleteCategory(catId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("分类已删除");
    }

    // ---------- 商品 ----------

    @GetMapping("/products")
    @RequirePermission("master:product:read")
    public ApiResponse listProducts(@RequestParam(defaultValue = "") String keyword,
                                    @RequestParam(required = false) Long categoryId,
                                    @RequestParam(defaultValue = "1") int page,
                                    @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(masterService.pageProducts(keyword, categoryId, page, pageSize));
    }

    @GetMapping("/products/all")
    @RequirePermission("master:product:read")
    public ApiResponse allProducts(@RequestParam(defaultValue = "active") String status) {
        return ApiResponse.ok(masterService.allProducts(status));
    }

    @PostMapping("/products")
    @RequirePermission("master:product:manage")
    public ApiResponse createProduct(@Valid @RequestBody MasterRequests.ProductBody body,
                                     HttpServletRequest request) {
        return ApiResponse.ok(masterService.createProduct(body, user(request).getUsername(),
                request.getRemoteAddr()), "商品创建成功");
    }

    @PutMapping("/products/{productId}")
    @RequirePermission("master:product:manage")
    public ApiResponse updateProduct(@PathVariable Long productId,
                                     @Valid @RequestBody MasterRequests.ProductBody body,
                                     HttpServletRequest request) {
        masterService.updateProduct(productId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("商品更新成功");
    }

    @DeleteMapping("/products/{productId}")
    @RequirePermission("master:product:manage")
    public ApiResponse deleteProduct(@PathVariable Long productId, HttpServletRequest request) {
        masterService.deleteProduct(productId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("商品已删除");
    }

    // ---------- 客户 ----------

    @GetMapping("/customers")
    @RequirePermission("master:customer:read")
    public ApiResponse listCustomers(@RequestParam(defaultValue = "") String keyword,
                                     @RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(masterService.pageCustomers(keyword, page, pageSize));
    }

    @GetMapping("/customers/all")
    @RequirePermission("master:customer:read")
    public ApiResponse allCustomers(@RequestParam(defaultValue = "active") String status) {
        return ApiResponse.ok(masterService.allCustomers(status));
    }

    @PostMapping("/customers")
    @RequirePermission("master:customer:manage")
    public ApiResponse createCustomer(@Valid @RequestBody MasterRequests.CustomerBody body,
                                      HttpServletRequest request) {
        return ApiResponse.ok(masterService.createCustomer(body, user(request).getUsername(),
                request.getRemoteAddr()), "客户创建成功");
    }

    @PutMapping("/customers/{custId}")
    @RequirePermission("master:customer:manage")
    public ApiResponse updateCustomer(@PathVariable Long custId,
                                      @Valid @RequestBody MasterRequests.CustomerBody body,
                                      HttpServletRequest request) {
        masterService.updateCustomer(custId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("客户更新成功");
    }

    @DeleteMapping("/customers/{custId}")
    @RequirePermission("master:customer:manage")
    public ApiResponse deleteCustomer(@PathVariable Long custId, HttpServletRequest request) {
        masterService.deleteCustomer(custId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("客户已删除");
    }

    // ---------- 供应商 ----------

    @GetMapping("/suppliers")
    @RequirePermission("master:supplier:read")
    public ApiResponse listSuppliers(@RequestParam(defaultValue = "") String keyword,
                                     @RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(masterService.pageSuppliers(keyword, page, pageSize));
    }

    @GetMapping("/suppliers/all")
    @RequirePermission("master:supplier:read")
    public ApiResponse allSuppliers(@RequestParam(defaultValue = "active") String status) {
        return ApiResponse.ok(masterService.allSuppliers(status));
    }

    @PostMapping("/suppliers")
    @RequirePermission("master:supplier:manage")
    public ApiResponse createSupplier(@Valid @RequestBody MasterRequests.SupplierBody body,
                                      HttpServletRequest request) {
        return ApiResponse.ok(masterService.createSupplier(body, user(request).getUsername(),
                request.getRemoteAddr()), "供应商创建成功");
    }

    @PutMapping("/suppliers/{supId}")
    @RequirePermission("master:supplier:manage")
    public ApiResponse updateSupplier(@PathVariable Long supId,
                                      @Valid @RequestBody MasterRequests.SupplierBody body,
                                      HttpServletRequest request) {
        masterService.updateSupplier(supId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("供应商更新成功");
    }

    @DeleteMapping("/suppliers/{supId}")
    @RequirePermission("master:supplier:manage")
    public ApiResponse deleteSupplier(@PathVariable Long supId, HttpServletRequest request) {
        masterService.deleteSupplier(supId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("供应商已删除");
    }

    // ---------- 仓库 ----------

    @GetMapping("/warehouses")
    @RequirePermission("master:warehouse:read")
    public ApiResponse listWarehouses() {
        return ApiResponse.ok(masterService.listWarehouses());
    }

    @PostMapping("/warehouses")
    @RequirePermission("master:warehouse:manage")
    public ApiResponse createWarehouse(@Valid @RequestBody MasterRequests.WarehouseBody body,
                                       HttpServletRequest request) {
        return ApiResponse.ok(masterService.createWarehouse(body, user(request).getUsername(),
                request.getRemoteAddr()), "仓库创建成功");
    }

    @PutMapping("/warehouses/{whId}")
    @RequirePermission("master:warehouse:manage")
    public ApiResponse updateWarehouse(@PathVariable Long whId,
                                       @Valid @RequestBody MasterRequests.WarehouseBody body,
                                       HttpServletRequest request) {
        masterService.updateWarehouse(whId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("仓库更新成功");
    }

    @DeleteMapping("/warehouses/{whId}")
    @RequirePermission("master:warehouse:manage")
    public ApiResponse deleteWarehouse(@PathVariable Long whId, HttpServletRequest request) {
        masterService.deleteWarehouse(whId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("仓库已删除");
    }
}
