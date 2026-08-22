package com.openerp.repository;

import com.openerp.entity.FinReceivable;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface FinReceivableRepository extends JpaRepository<FinReceivable, Long> {
    @Query("select r from FinReceivable r left join fetch r.customer where (:status is null or :status = '' or r.status = :status) and (:keyword is null or :keyword = '' or r.receivableNo like %:keyword% or r.sourceNo like %:keyword%) order by r.id desc")
    Page<FinReceivable> search(@Param("status") String status, @Param("keyword") String keyword, Pageable pageable);
}
