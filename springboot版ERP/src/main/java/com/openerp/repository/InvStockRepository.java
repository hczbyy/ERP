package com.openerp.repository;

import com.openerp.entity.InvStock;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface InvStockRepository extends JpaRepository<InvStock, Long> {
    Optional<InvStock> findByProductIdAndWarehouseId(Long productId, Long warehouseId);

    @Query("select s, p from InvStock s join MdProduct p on s.productId = p.id where (:warehouseId is null or s.warehouseId = :warehouseId) and (:keyword is null or :keyword = '' or p.name like %:keyword% or p.code like %:keyword%) and (:lowOnly = false or s.qty < p.safetyStock) order by s.id desc")
    Page<Object[]> searchStocks(@Param("warehouseId") Long warehouseId,
                                @Param("keyword") String keyword,
                                @Param("lowOnly") boolean lowOnly,
                                Pageable pageable);

    boolean existsByWarehouseId(Long warehouseId);

    @Query("select count(s) from InvStock s join MdProduct p on s.productId = p.id where s.qty < p.safetyStock")
    long countLowStock();

    @Query("select p.name, p.code, s.qty, p.safetyStock from InvStock s join MdProduct p on s.productId = p.id where s.qty < p.safetyStock order by (s.qty - p.safetyStock)")
    java.util.List<Object[]> findLowStocks(Pageable pageable);
}
