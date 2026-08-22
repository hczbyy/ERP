package com.openerp.service;

import com.openerp.audit.AuditService;
import com.openerp.common.AuthUser;
import com.openerp.common.BusinessException;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.AuthRequests;
import com.openerp.entity.SysPermission;
import com.openerp.entity.SysRole;
import com.openerp.entity.SysUser;
import com.openerp.repository.SysUserRepository;
import com.openerp.util.JwtUtil;
import com.openerp.util.PasswordUtil;
import com.openerp.util.Rows;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;

@Service
public class AuthService {
    private final SysUserRepository userRepository;
    private final JwtUtil jwtUtil;
    private final RedisTemplate<String, Object> redisTemplate;
    private final AuditService auditService;

    @Value("${openerp.jwt.expire-minutes}")
    private long expireMinutes;

    public AuthService(SysUserRepository userRepository, JwtUtil jwtUtil,
                       RedisTemplate<String, Object> redisTemplate, AuditService auditService) {
        this.userRepository = userRepository;
        this.jwtUtil = jwtUtil;
        this.redisTemplate = redisTemplate;
        this.auditService = auditService;
    }

    @Transactional
    public Map<String, Object> login(AuthRequests.LoginRequest req, String ip) {
        SysUser user = userRepository.findWithDetailsByUsername(req.username()).orElse(null);
        boolean ok = user != null && PasswordUtil.verify(req.password(), user.getPasswordHash());
        if (!ok) {
            auditService.write(req.username(), "login", "auth", "登录失败", null, ip);
            throw new BusinessException("用户名或密码错误");
        }
        if (!user.isActive()) {
            throw new BusinessException("账号已被禁用，请联系管理员");
        }
        String token = jwtUtil.createToken(user.getId(), user.getUsername());
        SecurityInterceptor.saveToken(redisTemplate, user.getId(), token, expireMinutes);
        auditService.write(user.getUsername(), "login", "auth", "登录成功", null, ip);
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("token", token);
        data.put("user", Rows.user(user));
        return data;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> me(AuthUser authUser) {
        SysUser user = userRepository.findWithRolesById(authUser.getId())
                .orElseThrow(() -> new BusinessException("用户不存在", HttpStatus.UNAUTHORIZED));
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("user", Rows.user(user));
        data.put("permissions", permissionsOf(user));
        return data;
    }

    @Transactional(readOnly = true)
    public List<String> permissionsOf(SysUser user) {
        if (user.isSuperuser()) return List.of("*");
        Set<String> codes = new TreeSet<>();
        for (SysRole role : user.getRoles()) {
            for (SysPermission p : role.getPermissions()) {
                codes.add(p.getCode());
            }
        }
        return new ArrayList<>(codes);
    }

    @Transactional
    public void changePassword(AuthUser authUser, AuthRequests.ChangePasswordRequest req, String ip) {
        SysUser user = userRepository.findById(authUser.getId())
                .orElseThrow(() -> new BusinessException("用户不存在"));
        if (!PasswordUtil.verify(req.oldPassword(), user.getPasswordHash())) {
            throw new BusinessException("原密码错误");
        }
        user.setPasswordHash(PasswordUtil.hash(req.newPassword()));
        userRepository.save(user);
        auditService.write(user.getUsername(), "update", "auth",
                "修改密码(user#" + user.getId() + ")", null, ip);
    }
}
