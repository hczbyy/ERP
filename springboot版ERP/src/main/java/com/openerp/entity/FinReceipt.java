package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "fin_receipt")
@Getter
@Setter
public class FinReceipt extends BaseEntity {
    @Column(name = "receipt_no", length = 30, unique = true, nullable = false)
    private String receiptNo;

    @Column(name = "receivable_id", nullable = false)
    private Long receivableId;

    @Column(name = "receivable_no", length = 30, nullable = false)
    private String receivableNo;

    @Column(name = "customer_id", nullable = false)
    private Long customerId;

    @Column(name = "amount", precision = 12, scale = 2, nullable = false)
    private BigDecimal amount;

    @Column(name = "pay_method", length = 10, nullable = false)
    private String payMethod = "bank";

    @Column(name = "received_at")
    private LocalDate receivedAt;

    @Column(name = "remark", columnDefinition = "TEXT")
    private String remark;

    @Column(name = "created_by", length = 50, nullable = false)
    private String createdBy;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "receivable_id", insertable = false, updatable = false)
    private FinReceivable receivable;
}
