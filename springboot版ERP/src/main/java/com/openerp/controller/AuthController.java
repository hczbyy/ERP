package com.openerp.controller;

import com.openerp.common.ApiResponse;
import com.openerp.common.AuthUser;
import com.openerp.config.SecurityInterceptor;
import com.openerp.dto.AuthRequests;
import com.openerp.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/auth")
public class AuthController {
    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping("/login")
    public ApiResponse login(@Valid @RequestBody AuthRequests.LoginRequest body, HttpServletRequest request) {
        return ApiResponse.ok(authService.login(body, request.getRemoteAddr()), "登录成功");
    }

    @GetMapping("/me")
    public ApiResponse me(HttpServletRequest request) {
        return ApiResponse.ok(authService.me(SecurityInterceptor.current(request)));
    }

    @GetMapping("/permissions")
    public ApiResponse permissions(HttpServletRequest request) {
        AuthUser user = SecurityInterceptor.current(request);
        return ApiResponse.ok(java.util.Map.of("permissions",
                user.isSuperuser() ? java.util.List.of("*") : user.getPermissions()));
    }

    @PostMapping("/change-password")
    public ApiResponse changePassword(@Valid @RequestBody AuthRequests.ChangePasswordRequest body,
                                      HttpServletRequest request) {
        authService.changePassword(SecurityInterceptor.current(request), body, request.getRemoteAddr());
        return ApiResponse.ok("密码修改成功");
    }
}
