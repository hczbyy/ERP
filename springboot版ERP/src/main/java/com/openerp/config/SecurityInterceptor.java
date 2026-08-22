package com.openerp.config;

import com.openerp.common.AuthUser;
import com.openerp.common.BusinessException;
import com.openerp.common.RequirePermission;
import com.openerp.entity.SysPermission;
import com.openerp.entity.SysRole;
import com.openerp.entity.SysUser;
import com.openerp.repository.SysUserRepository;
import com.openerp.util.JwtUtil;
import io.jsonwebtoken.Claims;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;

@Component
public class SecurityInterceptor implements HandlerInterceptor {
    public static final String AUTH_USER_ATTR = "authUser";
    private static final String TOKEN_KEY_PREFIX = "erp:token:";

    private final JwtUtil jwtUtil;
    private final SysUserRepository userRepository;
    private final RedisTemplate<String, Object> redisTemplate;

    public SecurityInterceptor(JwtUtil jwtUtil, SysUserRepository userRepository,
                               RedisTemplate<String, Object> redisTemplate) {
        this.jwtUtil = jwtUtil;
        this.userRepository = userRepository;
        this.redisTemplate = redisTemplate;
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        if (!(handler instanceof HandlerMethod handlerMethod)) {
            return true;
        }
        String auth = request.getHeader("Authorization");
        if (auth == null || !auth.startsWith("Bearer ")) {
            throw new BusinessException("未登录或登录已过期", HttpStatus.UNAUTHORIZED);
        }
        String token = auth.substring(7);
        Claims claims = jwtUtil.parse(token);
        if (claims == null || claims.getSubject() == null) {
            throw new BusinessException("登录凭证无效或已过期", HttpStatus.UNAUTHORIZED);
        }
        Long userId = Long.valueOf(claims.getSubject());
        Object stored = redisTemplate.opsForValue().get(TOKEN_KEY_PREFIX + userId);
        if (stored == null || !token.equals(String.valueOf(stored))) {
            throw new BusinessException("登录已过期，请重新登录", HttpStatus.UNAUTHORIZED);
        }

        SysUser user = userRepository.findWithDetailsByUsername(claims.get("username", String.class))
                .orElseThrow(() -> new BusinessException("用户不存在或已被禁用", HttpStatus.UNAUTHORIZED));
        if (!user.isActive()) {
            throw new BusinessException("用户不存在或已被禁用", HttpStatus.UNAUTHORIZED);
        }

        Set<String> codes = new HashSet<>();
        if (!user.isSuperuser()) {
            for (SysRole role : user.getRoles()) {
                for (SysPermission p : role.getPermissions()) {
                    codes.add(p.getCode());
                }
            }
        }
        AuthUser authUser = new AuthUser(user.getId(), user.getUsername(), user.getDisplayName(),
                user.isSuperuser(), user.isActive(), codes);
        request.setAttribute(AUTH_USER_ATTR, authUser);

        RequirePermission require = handlerMethod.getMethodAnnotation(RequirePermission.class);
        if (require != null && !authUser.hasPermission(require.value())) {
            throw new BusinessException("无权限：需要「" + require.value() + "」权限", HttpStatus.FORBIDDEN);
        }
        return true;
    }

    public static void saveToken(RedisTemplate<String, Object> redisTemplate, Long userId,
                                 String token, long expireMinutes) {
        redisTemplate.opsForValue().set(TOKEN_KEY_PREFIX + userId, token, expireMinutes, TimeUnit.MINUTES);
    }

    public static AuthUser current(HttpServletRequest request) {
        return (AuthUser) request.getAttribute(AUTH_USER_ATTR);
    }
}
