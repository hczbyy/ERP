package com.openerp.repository;

import com.openerp.entity.MdSupplier;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MdSupplierRepository extends JpaRepository<MdSupplier, Long> {
    boolean existsByCode(String code);

    @Query("select case when count(s) > 0 then true else false end from MdSupplier s where s.code = :code and s.id <> :id")
    boolean existsByCodeAndIdNot(@Param("code") String code, @Param("id") Long id);

    @Query("select s from MdSupplier s where :keyword is null or :keyword = '' or s.name like %:keyword% or s.code like %:keyword% order by s.id desc")
    Page<MdSupplier> search(@Param("keyword") String keyword, Pageable pageable);

    List<MdSupplier> findAllByStatusOrderByIdAsc(String status);
}
