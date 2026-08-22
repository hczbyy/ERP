package com.openerp.repository;

import com.openerp.entity.PoOrderItem;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PoOrderItemRepository extends JpaRepository<PoOrderItem, Long> {
    boolean existsByProductId(Long productId);
}
