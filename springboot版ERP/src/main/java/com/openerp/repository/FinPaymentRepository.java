package com.openerp.repository;

import com.openerp.entity.FinPayment;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface FinPaymentRepository extends JpaRepository<FinPayment, Long> {
    @Query("select p from FinPayment p left join fetch p.payable left join fetch p.payable.supplier where :keyword is null or :keyword = '' or p.paymentNo like %:keyword% order by p.id desc")
    Page<FinPayment> search(@Param("keyword") String keyword, Pageable pageable);
}
