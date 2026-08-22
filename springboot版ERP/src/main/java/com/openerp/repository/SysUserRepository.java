package com.openerp.repository;

import com.openerp.entity.SysUser;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.Optional;

public interface SysUserRepository extends JpaRepository<SysUser, Long> {
    Optional<SysUser> findByUsername(String username);

    boolean existsByUsername(String username);

    @Query("select distinct u from SysUser u left join fetch u.roles r left join fetch r.permissions where u.username = :username")
    Optional<SysUser> findWithDetailsByUsername(@Param("username") String username);

    @Query("select distinct u from SysUser u left join fetch u.roles where u.id = :id")
    Optional<SysUser> findWithRolesById(@Param("id") Long id);

    @Query("select u from SysUser u where :keyword is null or u.username like %:keyword% or u.displayName like %:keyword% order by u.id")
    Page<SysUser> search(@Param("keyword") String keyword, Pageable pageable);
}
