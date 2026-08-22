package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "so_stock_out")
@Getter
@Setter
public class SoStockOut extends BaseEntity {
    @Column(name = "stock_out_no", length = 30, unique = true, nullable = false)
    private String stockOutNo;

    @Column(name = "so_id", nullable = false)
    private Long soId;

    @Column(name = "so_no", length = 30, nullable = false)
    private String soNo;

    @Column(name = "customer_id", nullable = false)
    private Long customerId;

    @Column(name = "warehouse_id", nullable = false)
    private Long warehouseId;

    @Column(name = "total_amount", precision = 12, scale = 2)
    private BigDecimal totalAmount = BigDecimal.ZERO;

    @Column(name = "remark", columnDefinition = "TEXT")
    private String remark;

    @Column(name = "created_by", length = 50, nullable = false)
    private String createdBy;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "customer_id", insertable = false, updatable = false)
    private MdCustomer customer;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "warehouse_id", insertable = false, updatable = false)
    private MdWarehouse warehouse;

    @OneToMany(mappedBy = "stockOut", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("id ASC")
    private List<SoStockOutItem> items = new ArrayList<>();
}
