package com.openerp.repository;

import com.openerp.entity.FinPayable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface FinPayableRepository extends JpaRepository<FinPayable, Long> {
    @Query("select p from FinPayable p left join fetch p.supplier where (:status is null or :status = '' or p.status = :status) and (:keyword is null or :keyword = '' or p.payableNo like %:keyword% or p.sourceNo like %:keyword%) order by p.id desc")
    Page<FinPayable> search(@Param("status") String status, @Param("keyword") String keyword, Pageable pageable);
}
