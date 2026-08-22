package com.openerp.repository;

import com.openerp.entity.PoOrder;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface PoOrderRepository extends JpaRepository<PoOrder, Long> {
    long countByStatus(String status);

    @Query("select o from PoOrder o left join fetch o.items left join fetch o.supplier left join fetch o.warehouse where o.id = :id")
    Optional<PoOrder> findWithItemsById(@Param("id") Long id);

    @Query("select o from PoOrder o left join fetch o.supplier left join fetch o.warehouse where (:status is null or :status = '' or o.status = :status) and (:keyword is null or :keyword = '' or o.orderNo like %:keyword% or o.remark like %:keyword%) order by o.id desc")
    Page<PoOrder> search(@Param("status") String status, @Param("keyword") String keyword, Pageable pageable);
}
