package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "inv_stock_check")
@Getter
@Setter
public class InvStockCheck extends BaseEntity {
    @Column(name = "check_no", length = 30, unique = true, nullable = false)
    private String checkNo;

    @Column(name = "warehouse_id", nullable = false)
    private Long warehouseId;

    @Column(name = "status", length = 10, nullable = false)
    private String status = "draft";

    @Column(name = "remark", columnDefinition = "TEXT")
    private String remark;

    @Column(name = "created_by", length = 50, nullable = false)
    private String createdBy;

    @Column(name = "done_by", length = 50)
    private String doneBy;

    @Column(name = "done_at", length = 30)
    private LocalDateTime doneAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "warehouse_id", insertable = false, updatable = false)
    private MdWarehouse warehouse;

    @OneToMany(mappedBy = "check", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("id ASC")
    private List<InvStockCheckItem> items = new ArrayList<>();
}
