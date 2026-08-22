package com.openerp.repository;

import com.openerp.entity.AuditLog;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
    @Query("select a from AuditLog a where (:keyword is null or a.target like %:keyword%) and (:action is null or :action = '' or a.action = :action) order by a.id desc")
    Page<AuditLog> search(@Param("keyword") String keyword, @Param("action") String action, Pageable pageable);
}
