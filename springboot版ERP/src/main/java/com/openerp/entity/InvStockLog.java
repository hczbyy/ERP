package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "inv_stock_log")
@Getter
@Setter
public class InvStockLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "warehouse_id", nullable = false)
    private Long warehouseId;

    @Column(name = "change_qty", precision = 14, scale = 2, nullable = false)
    private BigDecimal changeQty;

    @Column(name = "before_qty", precision = 14, scale = 2, nullable = false)
    private BigDecimal beforeQty;

    @Column(name = "after_qty", precision = 14, scale = 2, nullable = false)
    private BigDecimal afterQty;

    @Column(name = "log_type", length = 20, nullable = false)
    private String logType;

    @Column(name = "ref_no", length = 30)
    private String refNo;

    @Column(name = "remark", columnDefinition = "TEXT")
    private String remark;

    @Column(name = "created_by", length = 50, nullable = false)
    private String createdBy;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", insertable = false, updatable = false)
    private MdProduct product;
}
