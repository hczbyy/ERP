package com.openerp.repository;

import com.openerp.entity.FinReceipt;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface FinReceiptRepository extends JpaRepository<FinReceipt, Long> {
    @Query("select r from FinReceipt r left join fetch r.receivable left join fetch r.receivable.customer where :keyword is null or :keyword = '' or r.receiptNo like %:keyword% order by r.id desc")
    Page<FinReceipt> search(@Param("keyword") String keyword, Pageable pageable);
}
