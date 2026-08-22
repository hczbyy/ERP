package com.openerp.repository;

import com.openerp.entity.SoOrder;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface SoOrderRepository extends JpaRepository<SoOrder, Long> {
    @Query("select o from SoOrder o left join fetch o.items left join fetch o.customer left join fetch o.warehouse where o.id = :id")
    Optional<SoOrder> findWithItemsById(@Param("id") Long id);

    @Query("select o from SoOrder o left join fetch o.customer left join fetch o.warehouse where (:status is null or :status = '' or o.status = :status) and (:keyword is null or :keyword = '' or o.orderNo like %:keyword% or o.remark like %:keyword%) order by o.id desc")
    Page<SoOrder> search(@Param("status") String status, @Param("keyword") String keyword, Pageable pageable);

    @Query("select o from SoOrder o left join fetch o.customer order by o.id desc")
    List<SoOrder> findRecent(Pageable pageable);

    long countByStatus(String status);
}
