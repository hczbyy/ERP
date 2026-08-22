package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;

@Entity
@Table(name = "inv_stock_check_item")
@Getter
@Setter
public class InvStockCheckItem {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "product_id", nullable = false)
    private Long productId;

    @Column(name = "book_qty", precision = 14, scale = 2, nullable = false)
    private BigDecimal bookQty;

    @Column(name = "actual_qty", precision = 14, scale = 2)
    private BigDecimal actualQty = BigDecimal.ZERO;

    @Column(name = "diff_qty", precision = 14, scale = 2)
    private BigDecimal diffQty = BigDecimal.ZERO;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "check_id")
    private InvStockCheck check;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "product_id", insertable = false, updatable = false)
    private MdProduct product;
}
