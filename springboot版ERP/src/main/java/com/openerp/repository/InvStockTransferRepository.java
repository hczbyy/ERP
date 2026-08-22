package com.openerp.repository;

import com.openerp.entity.InvStockTransfer;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface InvStockTransferRepository extends JpaRepository<InvStockTransfer, Long> {
    @Query("select t from InvStockTransfer t left join fetch t.fromWarehouse left join fetch t.toWarehouse order by t.id desc")
    Page<InvStockTransfer> findAllWithWarehouses(Pageable pageable);
}
