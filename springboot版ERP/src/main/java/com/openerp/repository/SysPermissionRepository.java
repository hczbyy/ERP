package com.openerp.repository;

import com.openerp.entity.SysPermission;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface SysPermissionRepository extends JpaRepository<SysPermission, Long> {
    List<SysPermission> findAllByOrderByModuleAscIdAsc();
}
