package com.openerp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.util.List;

public final class InventoryRequests {
    private InventoryRequests() {
    }

    public record CheckCreateBody(@NotNull @Positive @JsonProperty("warehouse_id") Long warehouseId,
                                  String remark,
                                  @NotEmpty @JsonProperty("product_ids") List<@NotNull @Positive Long> productIds) {
    }

    public record CheckItemBody(@NotNull @Positive @JsonProperty("product_id") Long productId,
                                @JsonProperty("actual_qty") int actualQty) {
    }

    public record CheckUpdateBody(@NotEmpty @Valid List<CheckItemBody> items) {
    }

    public record TransferItemBody(@NotNull @Positive @JsonProperty("product_id") Long productId, int qty) {
    }

    public record TransferBody(@NotNull @Positive @JsonProperty("from_warehouse_id") Long fromWarehouseId,
                               @NotNull @Positive @JsonProperty("to_warehouse_id") Long toWarehouseId,
                               String remark,
                               @NotEmpty @Valid List<TransferItemBody> items) {
    }
}
