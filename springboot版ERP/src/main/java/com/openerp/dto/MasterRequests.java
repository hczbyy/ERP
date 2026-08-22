package com.openerp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

public final class MasterRequests {
    private MasterRequests() {
    }

    public record CategoryBody(@NotBlank @Size(max = 50) String name, int sort) {
    }

    public record ProductBody(
            @NotBlank @Size(max = 50) String code,
            @NotBlank @Size(max = 100) String name,
            String spec,
            @NotBlank @Size(max = 20) String unit,
            String barcode,
            @JsonProperty("category_id") Long categoryId,
            @JsonProperty("purchase_price") BigDecimal purchasePrice,
            @JsonProperty("sale_price") BigDecimal salePrice,
            @JsonProperty("safety_stock") BigDecimal safetyStock,
            String status,
            String description) {
    }

    public record CustomerBody(
            @NotBlank @Size(max = 20) String code,
            @NotBlank @Size(max = 100) String name,
            String contact,
            String phone,
            String address,
            @JsonProperty("credit_limit") BigDecimal creditLimit,
            String status) {
    }

    public record SupplierBody(
            @NotBlank @Size(max = 20) String code,
            @NotBlank @Size(max = 100) String name,
            String contact,
            String phone,
            String address,
            String status) {
    }

    public record WarehouseBody(
            @NotBlank @Size(max = 20) String code,
            @NotBlank @Size(max = 50) String name,
            String address,
            String manager,
            String status) {
    }
}
