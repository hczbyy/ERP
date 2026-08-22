package com.openerp.controller;

import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.common.RequirePermission;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.SystemRequests;
import com.openerp.service.SystemService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/system")
public class SystemController {
    private final SystemService systemService;

    public SystemController(SystemService systemService) {
        this.systemService = systemService;
    }

    private AuthUser user(HttpServletRequest request) {
        return SecurityInterceptor.current(request);
    }

    @GetMapping("/users")
    @RequirePermission("system:user:manage")
    public ApiResponse listUsers(@RequestParam(defaultValue = "") String keyword,
                                 @RequestParam(defaultValue = "1") int page,
                                 @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(systemService.pageUsers(keyword, page, pageSize));
    }

    @PostMapping("/users")
    @RequirePermission("system:user:manage")
    public ApiResponse createUser(@Valid @RequestBody SystemRequests.UserBody body,
                                  HttpServletRequest request) {
        return ApiResponse.ok(systemService.createUser(body, user(request).getUsername(),
                request.getRemoteAddr()), "用户创建成功");
    }

    @PutMapping("/users/{userId}")
    @RequirePermission("system:user:manage")
    public ApiResponse updateUser(@PathVariable Long userId,
                                  @Valid @RequestBody SystemRequests.UserBody body,
                                  HttpServletRequest request) {
        return ApiResponse.ok(systemService.updateUser(userId, body, user(request).getUsername(),
                request.getRemoteAddr()), "用户更新成功");
    }

    @PostMapping("/users/{userId}/toggle-active")
    @RequirePermission("system:user:manage")
    public ApiResponse toggleUser(@PathVariable Long userId, HttpServletRequest request) {
        return ApiResponse.ok(systemService.toggleUser(userId, user(request), request.getRemoteAddr()),
                "操作成功");
    }

    @DeleteMapping("/users/{userId}")
    @RequirePermission("system:user:manage")
    public ApiResponse deleteUser(@PathVariable Long userId, HttpServletRequest request) {
        systemService.deleteUser(userId, user(request), request.getRemoteAddr());
        return ApiResponse.ok("用户已删除");
    }

    @GetMapping("/roles")
    @RequirePermission("system:role:manage")
    public ApiResponse listRoles() {
        return ApiResponse.ok(systemService.listRoles());
    }

    @GetMapping("/permissions")
    public ApiResponse listPermissions() {
        return ApiResponse.ok(systemService.listPermissions());
    }

    @PostMapping("/roles")
    @RequirePermission("system:role:manage")
    public ApiResponse createRole(@Valid @RequestBody SystemRequests.RoleBody body,
                                  HttpServletRequest request) {
        return ApiResponse.ok(systemService.createRole(body, user(request).getUsername(),
                request.getRemoteAddr()), "角色创建成功");
    }

    @PutMapping("/roles/{roleId}")
    @RequirePermission("system:role:manage")
    public ApiResponse updateRole(@PathVariable Long roleId,
                                  @Valid @RequestBody SystemRequests.RoleBody body,
                                  HttpServletRequest request) {
        systemService.updateRole(roleId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("角色更新成功");
    }

    @DeleteMapping("/roles/{roleId}")
    @RequirePermission("system:role:manage")
    public ApiResponse deleteRole(@PathVariable Long roleId, HttpServletRequest request) {
        systemService.deleteRole(roleId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("角色已删除");
    }

    @GetMapping("/departments")
    @RequirePermission("system:org:manage")
    public ApiResponse listDepartments() {
        return ApiResponse.ok(systemService.listDepartments());
    }

    @PostMapping("/departments")
    @RequirePermission("system:org:manage")
    public ApiResponse createDepartment(@Valid @RequestBody SystemRequests.DeptBody body,
                                        HttpServletRequest request) {
        return ApiResponse.ok(systemService.createDepartment(body, user(request).getUsername(),
                request.getRemoteAddr()), "部门创建成功");
    }

    @PutMapping("/departments/{deptId}")
    @RequirePermission("system:org:manage")
    public ApiResponse updateDepartment(@PathVariable Long deptId,
                                        @Valid @RequestBody SystemRequests.DeptBody body,
                                        HttpServletRequest request) {
        systemService.updateDepartment(deptId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("部门更新成功");
    }

    @DeleteMapping("/departments/{deptId}")
    @RequirePermission("system:org:manage")
    public ApiResponse deleteDepartment(@PathVariable Long deptId, HttpServletRequest request) {
        systemService.deleteDepartment(deptId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("部门已删除");
    }

    @GetMapping("/employees")
    @RequirePermission("system:org:manage")
    public ApiResponse listEmployees(@RequestParam(defaultValue = "") String keyword,
                                     @RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(systemService.pageEmployees(keyword, page, pageSize));
    }

    @PostMapping("/employees")
    @RequirePermission("system:org:manage")
    public ApiResponse createEmployee(@Valid @RequestBody SystemRequests.EmployeeBody body,
                                      HttpServletRequest request) {
        return ApiResponse.ok(systemService.createEmployee(body, user(request).getUsername(),
                request.getRemoteAddr()), "员工创建成功");
    }

    @PutMapping("/employees/{empId}")
    @RequirePermission("system:org:manage")
    public ApiResponse updateEmployee(@PathVariable Long empId,
                                      @Valid @RequestBody SystemRequests.EmployeeBody body,
                                      HttpServletRequest request) {
        systemService.updateEmployee(empId, body, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("员工更新成功");
    }

    @DeleteMapping("/employees/{empId}")
    @RequirePermission("system:org:manage")
    public ApiResponse deleteEmployee(@PathVariable Long empId, HttpServletRequest request) {
        systemService.deleteEmployee(empId, user(request).getUsername(), request.getRemoteAddr());
        return ApiResponse.ok("员工已删除");
    }

    @GetMapping("/audit-logs")
    @RequirePermission("system:audit:read")
    public ApiResponse listAuditLogs(@RequestParam(defaultValue = "") String keyword,
                                     @RequestParam(defaultValue = "") String action,
                                     @RequestParam(defaultValue = "1") int page,
                                     @RequestParam(defaultValue = "20") int pageSize) {
        return ApiResponse.ok(systemService.pageAuditLogs(keyword, action, page, pageSize));
    }
}
