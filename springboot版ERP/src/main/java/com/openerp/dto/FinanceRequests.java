package com.openerp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;

public final class FinanceRequests {
    private FinanceRequests() {
    }

    public record ReceivableCreateBody(@NotNull @Positive @JsonProperty("customer_id") Long customerId,
                                       @NotNull @Positive BigDecimal amount,
                                       @JsonProperty("due_date") String dueDate,
                                       String remark) {
    }

    public record PayableCreateBody(@NotNull @Positive @JsonProperty("supplier_id") Long supplierId,
                                    @NotNull @Positive BigDecimal amount,
                                    @JsonProperty("due_date") String dueDate,
                                    String remark) {
    }

    public record ReceiptBody(@NotNull @Positive @JsonProperty("receivable_id") Long receivableId,
                              @NotNull @Positive BigDecimal amount,
                              @JsonProperty("pay_method") String payMethod,
                              @JsonProperty("received_at") String receivedAt,
                              String remark) {
    }

    public record PaymentBody(@NotNull @Positive @JsonProperty("payable_id") Long payableId,
                              @NotNull @Positive BigDecimal amount,
                              @JsonProperty("pay_method") String payMethod,
                              @JsonProperty("paid_at") String paidAt,
                              String remark) {
    }
}
