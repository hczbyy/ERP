package com.openerp.repository;

import com.openerp.entity.SoOrderItem;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SoOrderItemRepository extends JpaRepository<SoOrderItem, Long> {
    boolean existsByProductId(Long productId);
}
