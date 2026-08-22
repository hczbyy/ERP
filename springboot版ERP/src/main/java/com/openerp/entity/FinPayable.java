package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "fin_payable")
@Getter
@Setter
public class FinPayable extends BaseEntity {
    @Column(name = "payable_no", length = 30, unique = true, nullable = false)
    private String payableNo;

    @Column(name = "source_no", length = 30, nullable = false)
    private String sourceNo;

    @Column(name = "supplier_id", nullable = false)
    private Long supplierId;

    @Column(name = "total_amount", precision = 12, scale = 2, nullable = false)
    private BigDecimal totalAmount;

    @Column(name = "paid_amount", precision = 12, scale = 2)
    private BigDecimal paidAmount = BigDecimal.ZERO;

    @Column(name = "status", length = 10, nullable = false)
    private String status = "open";

    @Column(name = "due_date")
    private LocalDate dueDate;

    @Column(name = "remark", columnDefinition = "TEXT")
    private String remark;

    @Column(name = "created_by", length = 50, nullable = false)
    private String createdBy;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "supplier_id", insertable = false, updatable = false)
    private MdSupplier supplier;

    @OneToMany(mappedBy = "payable", fetch = FetchType.LAZY)
    private List<FinPayment> payments = new ArrayList<>();
}
