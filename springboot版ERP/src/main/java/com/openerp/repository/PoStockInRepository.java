package com.openerp.repository;

import com.openerp.entity.PoStockIn;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface PoStockInRepository extends JpaRepository<PoStockIn, Long> {
    @Query("select s from PoStockIn s left join fetch s.supplier left join fetch s.warehouse where :keyword is null or :keyword = '' or s.stockInNo like %:keyword% or s.poNo like %:keyword% order by s.id desc")
    Page<PoStockIn> search(@Param("keyword") String keyword, Pageable pageable);

    @Query("select s from PoStockIn s left join fetch s.items left join fetch s.supplier left join fetch s.warehouse where s.id = :id")
    com.openerp.entity.PoStockIn findDetailById(@Param("id") Long id);
}
