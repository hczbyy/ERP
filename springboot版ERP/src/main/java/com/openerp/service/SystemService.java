package com.openerp.service;

import com.openerp.audit.AuditService;
import com.openerp.common.AuthUser;
import com.openerp.common.BusinessException;
import com.openerp.common.PageResult;
import com.openerp.dto.SystemRequests;
import com.openerp.entity.*;
import com.openerp.repository.*;
import com.openerp.util.PasswordUtil;
import com.openerp.util.Rows;
import com.openerp.util.Validators;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.*;

@Service
public class SystemService {
    private final SysUserRepository userRepository;
    private final SysRoleRepository roleRepository;
    private final SysPermissionRepository permissionRepository;
    private final OrgDepartmentRepository departmentRepository;
    private final OrgEmployeeRepository employeeRepository;
    private final AuditLogRepository auditLogRepository;
    private final AuditService auditService;

    public SystemService(SysUserRepository userRepository,
                         SysRoleRepository roleRepository,
                         SysPermissionRepository permissionRepository,
                         OrgDepartmentRepository departmentRepository,
                         OrgEmployeeRepository employeeRepository,
                         AuditLogRepository auditLogRepository,
                         AuditService auditService) {
        this.userRepository = userRepository;
        this.roleRepository = roleRepository;
        this.permissionRepository = permissionRepository;
        this.departmentRepository = departmentRepository;
        this.employeeRepository = employeeRepository;
        this.auditLogRepository = auditLogRepository;
        this.auditService = auditService;
    }

    // ---------------- 用户 ----------------

    @Transactional(readOnly = true)
    public PageResult pageUsers(String keyword, int pageNo, int pageSize) {
        Page<SysUser> p = userRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::user).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createUser(SystemRequests.UserBody body, String username, String ip) {
        if (userRepository.existsByUsername(body.username())) {
            throw new BusinessException("用户名 " + body.username() + " 已存在");
        }
        SysUser u = new SysUser();
        u.setUsername(body.username());
        u.setDisplayName(body.displayName());
        u.setPasswordHash(PasswordUtil.hash(body.password() == null || body.password().isBlank()
                ? "123456" : body.password()));
        u.setEmail(body.email());
        u.setPhone(body.phone());
        if (body.roleIds() != null && !body.roleIds().isEmpty()) {
            u.setRoles(new java.util.LinkedHashSet<>(roleRepository.findAllById(body.roleIds())));
        }
        userRepository.save(u);
        auditService.write(username, "create", "system", "用户 " + body.username(), null, ip);
        return Rows.user(u);
    }

    @Transactional
    public Map<String, Object> updateUser(Long id, SystemRequests.UserBody body, String username, String ip) {
        SysUser u = userRepository.findById(id)
                .orElseThrow(() -> new BusinessException("用户不存在"));
        if (!u.getUsername().equals(body.username()) && userRepository.existsByUsername(body.username())) {
            throw new BusinessException("用户名 " + body.username() + " 已存在");
        }
        u.setUsername(body.username());
        u.setDisplayName(body.displayName());
        u.setEmail(body.email());
        u.setPhone(body.phone());
        if (body.password() != null && !body.password().isBlank()) {
            u.setPasswordHash(PasswordUtil.hash(body.password()));
        }
        if (body.roleIds() != null) {
            u.setRoles(new java.util.LinkedHashSet<>(roleRepository.findAllById(body.roleIds())));
        }
        userRepository.save(u);
        auditService.write(username, "update", "system", "用户 " + u.getUsername(), null, ip);
        return Rows.user(u);
    }

    @Transactional
    public Map<String, Object> toggleUser(Long id, AuthUser op, String ip) {
        SysUser u = userRepository.findById(id)
                .orElseThrow(() -> new BusinessException("用户不存在"));
        if (u.getId().equals(op.getId())) {
            throw new BusinessException("不能禁用自己");
        }
        if (u.isSuperuser()) {
            throw new BusinessException("不能禁用超级管理员");
        }
        u.setActive(!u.isActive());
        userRepository.save(u);
        auditService.write(op.getUsername(), "update", "system",
                (u.isActive() ? "启用" : "禁用") + "用户 " + u.getUsername(), null, ip);
        return Rows.user(u);
    }

    @Transactional
    public void deleteUser(Long id, AuthUser op, String ip) {
        SysUser u = userRepository.findById(id)
                .orElseThrow(() -> new BusinessException("用户不存在"));
        if (u.getId().equals(op.getId())) {
            throw new BusinessException("不能删除自己");
        }
        if (u.isSuperuser()) {
            throw new BusinessException("不能删除超级管理员");
        }
        userRepository.delete(u);
        auditService.write(op.getUsername(), "delete", "system", "用户 " + u.getUsername(), null, ip);
    }

    // ---------------- 角色与权限 ----------------

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listRoles() {
        return roleRepository.findAllWithPermissions().stream().map(Rows::role).toList();
    }

    @Transactional(readOnly = true)
    public Map<String, Object> listPermissions() {
        Map<String, List<Map<String, Object>>> groups = new LinkedHashMap<>();
        for (SysPermission p : permissionRepository.findAllByOrderByModuleAscIdAsc()) {
            groups.computeIfAbsent(p.getModule(), k -> new ArrayList<>())
                    .add(Map.of("id", p.getId(), "code", p.getCode(), "name", p.getName()));
        }
        return Map.of("groups", groups);
    }

    @Transactional
    public Map<String, Object> createRole(SystemRequests.RoleBody body, String username, String ip) {
        if (roleRepository.existsByCode(body.code())) {
            throw new BusinessException("角色编码 " + body.code() + " 已存在");
        }
        SysRole role = new SysRole();
        role.setCode(body.code());
        role.setName(body.name());
        role.setDescription(body.description());
        if (body.permissionIds() != null && !body.permissionIds().isEmpty()) {
            role.setPermissions(new java.util.LinkedHashSet<>(permissionRepository.findAllById(body.permissionIds())));
        }
        roleRepository.save(role);
        auditService.write(username, "create", "system", "角色 " + body.name(), null, ip);
        return Map.of("id", role.getId());
    }

    @Transactional
    public void updateRole(Long id, SystemRequests.RoleBody body, String username, String ip) {
        SysRole role = roleRepository.findById(id)
                .orElseThrow(() -> new BusinessException("角色不存在"));
        Optional<SysRole> dup = roleRepository.findByCode(body.code());
        if (dup.isPresent() && !dup.get().getId().equals(id)) {
            throw new BusinessException("角色编码 " + body.code() + " 已存在");
        }
        role.setCode(body.code());
        role.setName(body.name());
        role.setDescription(body.description());
        role.setPermissions(new java.util.LinkedHashSet<>(permissionRepository.findAllById(
                body.permissionIds() == null ? List.of() : body.permissionIds())));
        roleRepository.save(role);
        auditService.write(username, "update", "system", "角色 " + body.name(), null, ip);
    }

    @Transactional
    public void deleteRole(Long id, String username, String ip) {
        SysRole role = roleRepository.findById(id)
                .orElseThrow(() -> new BusinessException("角色不存在"));
        if (role.isBuiltin()) {
            throw new BusinessException("内置角色不可删除");
        }
        if (role.getUsers() != null && !role.getUsers().isEmpty()) {
            throw new BusinessException("该角色已分配给用户，无法删除");
        }
        roleRepository.delete(role);
        auditService.write(username, "delete", "system", "角色 " + role.getName(), null, ip);
    }

    // ---------------- 部门 ----------------

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listDepartments() {
        return departmentRepository.findAllByOrderByIdAsc().stream().map(Rows::dept).toList();
    }

    @Transactional
    public Map<String, Object> createDepartment(SystemRequests.DeptBody body, String username, String ip) {
        if (departmentRepository.existsByCode(body.code())) {
            throw new BusinessException("部门编码 " + body.code() + " 已存在");
        }
        OrgDepartment d = new OrgDepartment();
        d.setCode(body.code());
        d.setName(body.name());
        d.setLeader(body.leader());
        d.setPhone(body.phone());
        d.setRemark(body.remark());
        departmentRepository.save(d);
        auditService.write(username, "create", "system", "部门 " + body.name(), null, ip);
        return Map.of("id", d.getId());
    }

    @Transactional
    public void updateDepartment(Long id, SystemRequests.DeptBody body, String username, String ip) {
        OrgDepartment d = departmentRepository.findById(id)
                .orElseThrow(() -> new BusinessException("部门不存在"));
        if (departmentRepository.existsByCodeAndIdNot(body.code(), id)) {
            throw new BusinessException("部门编码 " + body.code() + " 已存在");
        }
        d.setCode(body.code());
        d.setName(body.name());
        d.setLeader(body.leader());
        d.setPhone(body.phone());
        d.setRemark(body.remark());
        departmentRepository.save(d);
        auditService.write(username, "update", "system", "部门 " + body.name(), null, ip);
    }

    @Transactional
    public void deleteDepartment(Long id, String username, String ip) {
        OrgDepartment d = departmentRepository.findById(id)
                .orElseThrow(() -> new BusinessException("部门不存在"));
        if (employeeRepository.findAll().stream().anyMatch(e -> id.equals(e.getDepartmentId()))) {
            throw new BusinessException("该部门下存在员工，无法删除");
        }
        departmentRepository.delete(d);
        auditService.write(username, "delete", "system", "部门 " + d.getName(), null, ip);
    }

    // ---------------- 员工 ----------------

    @Transactional(readOnly = true)
    public PageResult pageEmployees(String keyword, int pageNo, int pageSize) {
        Page<OrgEmployee> p = employeeRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::emp).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createEmployee(SystemRequests.EmployeeBody body, String username, String ip) {
        if (employeeRepository.existsByEmpNo(body.empNo())) {
            throw new BusinessException("工号 " + body.empNo() + " 已存在");
        }
        OrgEmployee e = new OrgEmployee();
        fillEmployee(e, body);
        employeeRepository.save(e);
        auditService.write(username, "create", "system", "员工 " + body.name(), null, ip);
        return Map.of("id", e.getId());
    }

    @Transactional
    public void updateEmployee(Long id, SystemRequests.EmployeeBody body, String username, String ip) {
        OrgEmployee e = employeeRepository.findById(id)
                .orElseThrow(() -> new BusinessException("员工不存在"));
        if (employeeRepository.existsByEmpNoAndIdNot(body.empNo(), id)) {
            throw new BusinessException("工号 " + body.empNo() + " 已存在");
        }
        fillEmployee(e, body);
        employeeRepository.save(e);
        auditService.write(username, "update", "system", "员工 " + body.name(), null, ip);
    }

    private void fillEmployee(OrgEmployee e, SystemRequests.EmployeeBody body) {
        e.setEmpNo(body.empNo());
        e.setName(body.name());
        e.setGender(body.gender());
        e.setPhone(body.phone());
        e.setEmail(body.email());
        e.setHireDate(Validators.parseDate(body.hireDate(), "入职日期"));
        e.setPosition(body.position());
        e.setStatus(body.status() == null || body.status().isBlank() ? "active" : body.status());
        e.setDepartmentId(body.departmentId());
    }

    @Transactional
    public void deleteEmployee(Long id, String username, String ip) {
        OrgEmployee e = employeeRepository.findById(id)
                .orElseThrow(() -> new BusinessException("员工不存在"));
        employeeRepository.delete(e);
        auditService.write(username, "delete", "system", "员工 " + e.getName(), null, ip);
    }

    // ---------------- 审计日志 ----------------

    @Transactional(readOnly = true)
    public PageResult pageAuditLogs(String keyword, String action, int pageNo, int pageSize) {
        Page<AuditLog> p = auditLogRepository.search(keyword, action,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        List<Map<String, Object>> items = p.getContent().stream().map(a -> {
            Map<String, Object> m = Rows.map(
                    "id", a.getId(), "username", a.getUsername(), "action", a.getAction(),
                    "module", a.getModule(), "target", a.getTarget(), "detail", a.getDetail(),
                    "ip", a.getIp(), "created_at", a.getCreatedAt());
            return m;
        }).toList();
        return new PageResult(items, p.getTotalElements(), pageNo, pageSize);
    }
}
