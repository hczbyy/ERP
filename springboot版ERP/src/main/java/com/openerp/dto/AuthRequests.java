package com.openerp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public final class AuthRequests {
    private AuthRequests() {
    }

    public record LoginRequest(
            @NotBlank(message = "缺少必填字段「username」") @Size(max = 50) String username,
            @NotBlank(message = "缺少必填字段「password」") @Size(max = 100) String password) {
    }

    public record ChangePasswordRequest(
            @NotBlank @JsonProperty("old_password") String oldPassword,
            @NotBlank @Size(min = 6, max = 100) @JsonProperty("new_password") String newPassword) {
    }
}
