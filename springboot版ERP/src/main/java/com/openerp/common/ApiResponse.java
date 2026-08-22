package com.openerp.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class ApiResponse {
    private final int code;
    private final String message;
    private final Object data;

    public static ApiResponse ok(Object data) {
        return new ApiResponse(0, "success", data);
    }

    public static ApiResponse ok(Object data, String message) {
        return new ApiResponse(0, message, data);
    }

    public static ApiResponse ok(String message) {
        return new ApiResponse(0, message, null);
    }

    public static ApiResponse fail(String message) {
        return new ApiResponse(1, message, null);
    }
}
