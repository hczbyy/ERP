package com.openerp.repository;

import com.openerp.entity.InvStockCheck;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface InvStockCheckRepository extends JpaRepository<InvStockCheck, Long> {
    @Query("select c from InvStockCheck c left join fetch c.warehouse where (:status is null or :status = '' or c.status = :status) order by c.id desc")
    Page<InvStockCheck> search(@Param("status") String status, Pageable pageable);

    @Query("select c from InvStockCheck c left join fetch c.items left join fetch c.warehouse where c.id = :id")
    Optional<InvStockCheck> findWithItemsById(@Param("id") Long id);
}
