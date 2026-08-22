package com.openerp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.util.List;

public final class SystemRequests {
    private SystemRequests() {
    }

    public record UserBody(@NotBlank @Size(min = 2, max = 50) String username,
                           @NotBlank @Size(max = 50) @JsonProperty("display_name") String displayName,
                           @Size(min = 6, max = 100) String password,
                           String email,
                           String phone,
                           @JsonProperty("role_ids") List<Long> roleIds) {
    }

    public record RoleBody(@NotBlank @Size(max = 50) String code,
                           @NotBlank @Size(max = 50) String name,
                           String description,
                           @JsonProperty("permission_ids") List<Long> permissionIds) {
    }

    public record DeptBody(@NotBlank @Size(max = 20) String code,
                           @NotBlank @Size(max = 50) String name,
                           String leader,
                           String phone,
                           String remark) {
    }

    public record EmployeeBody(@NotBlank @Size(max = 20) @JsonProperty("emp_no") String empNo,
                               @NotBlank @Size(max = 50) String name,
                               String gender,
                               String phone,
                               String email,
                               @JsonProperty("hire_date") String hireDate,
                               String position,
                               String status,
                               @JsonProperty("department_id") Long departmentId) {
    }
}
