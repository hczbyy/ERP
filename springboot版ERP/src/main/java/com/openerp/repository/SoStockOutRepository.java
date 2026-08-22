package com.openerp.repository;

import com.openerp.entity.SoStockOut;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface SoStockOutRepository extends JpaRepository<SoStockOut, Long> {
    @Query("select s from SoStockOut s left join fetch s.customer left join fetch s.warehouse where :keyword is null or :keyword = '' or s.stockOutNo like %:keyword% or s.soNo like %:keyword% order by s.id desc")
    Page<SoStockOut> search(@Param("keyword") String keyword, Pageable pageable);

    @Query("select s from SoStockOut s left join fetch s.items left join fetch s.customer left join fetch s.warehouse where s.id = :id")
    com.openerp.entity.SoStockOut findDetailById(@Param("id") Long id);
}
