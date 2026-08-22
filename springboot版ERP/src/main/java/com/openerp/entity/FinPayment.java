package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;

@Entity
@Table(name = "fin_payment")
@Getter
@Setter
public class FinPayment extends BaseEntity {
    @Column(name = "payment_no", length = 30, unique = true, nullable = false)
    private String paymentNo;

    @Column(name = "payable_id", nullable = false)
    private Long payableId;

    @Column(name = "payable_no", length = 30, nullable = false)
    private String payableNo;

    @Column(name = "supplier_id", nullable = false)
    private Long supplierId;

    @Column(name = "amount", precision = 12, scale = 2, nullable = false)
    private BigDecimal amount;

    @Column(name = "pay_method", length = 10, nullable = false)
    private String payMethod = "bank";

    @Column(name = "paid_at")
    private LocalDate paidAt;

    @Column(name = "remark", columnDefinition = "TEXT")
    private String remark;

    @Column(name = "created_by", length = 50, nullable = false)
    private String createdBy;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "payable_id", insertable = false, updatable = false)
    private FinPayable payable;
}
