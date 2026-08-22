package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;

@Entity
@Table(name = "md_product")
@Getter
@Setter
public class MdProduct extends BaseEntity {
    @Column(name = "code", length = 50, unique = true, nullable = false)
    private String code;

    @Column(name = "name", length = 100, nullable = false)
    private String name;

    @Column(name = "spec", length = 100)
    private String spec;

    @Column(name = "unit", length = 20, nullable = false)
    private String unit = "件";

    @Column(name = "barcode", length = 50)
    private String barcode;

    @Column(name = "category_id")
    private Long categoryId;

    @Column(name = "purchase_price", precision = 12, scale = 2)
    private BigDecimal purchasePrice = BigDecimal.ZERO;

    @Column(name = "sale_price", precision = 12, scale = 2)
    private BigDecimal salePrice = BigDecimal.ZERO;

    @Column(name = "safety_stock", precision = 12, scale = 2)
    private BigDecimal safetyStock = BigDecimal.ZERO;

    @Column(name = "status", length = 10, nullable = false)
    private String status = "active";

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id", insertable = false, updatable = false)
    private MdCategory category;
}
