package com.openerp.repository;

import com.openerp.entity.SysRole;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.util.List;
import java.util.Optional;

public interface SysRoleRepository extends JpaRepository<SysRole, Long> {
    boolean existsByCode(String code);

    Optional<SysRole> findByCode(String code);

    @Query("select distinct r from SysRole r left join fetch r.permissions order by r.id")
    List<SysRole> findAllWithPermissions();

    @Query("select r from SysRole r left join fetch r.permissions where r.id = :id")
    Optional<SysRole> findWithPermissionsById(Long id);
}
