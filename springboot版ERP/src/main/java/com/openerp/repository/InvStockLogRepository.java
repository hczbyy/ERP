package com.openerp.repository;

import com.openerp.entity.InvStockLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InvStockLogRepository extends JpaRepository<InvStockLog, Long> {
    @Query("select l from InvStockLog l left join fetch l.product where (:productId is null or l.productId = :productId) and (:warehouseId is null or l.warehouseId = :warehouseId) and (:logType is null or :logType = '' or l.logType = :logType) order by l.id desc")
    Page<InvStockLog> search(@Param("productId") Long productId,
                             @Param("warehouseId") Long warehouseId,
                             @Param("logType") String logType,
                             Pageable pageable);
}
