package com.openerp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;
import java.util.List;

public final class OrderRequests {
    private OrderRequests() {
    }

    public record OrderItem(@NotNull @Positive @JsonProperty("product_id") Long productId,
                            @NotNull BigDecimal qty,
                            @NotNull BigDecimal price) {
    }

    public record PurchaseOrderBody(@NotNull @Positive @JsonProperty("supplier_id") Long supplierId,
                                    @NotNull @Positive @JsonProperty("warehouse_id") Long warehouseId,
                                    String remark,
                                    @NotEmpty @Valid List<OrderItem> items) {
    }

    public record SalesOrderBody(@NotNull @Positive @JsonProperty("customer_id") Long customerId,
                                 @NotNull @Positive @JsonProperty("warehouse_id") Long warehouseId,
                                 String remark,
                                 @NotEmpty @Valid List<OrderItem> items) {
    }

    public record CancelBody(String reason) {
    }

    public record ReceiveShipBody(String remark, @NotEmpty @Valid List<OrderItem> items) {
    }
}
