package com.openerp.repository;

import com.openerp.entity.MdCustomer;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MdCustomerRepository extends JpaRepository<MdCustomer, Long> {
    boolean existsByCode(String code);

    @Query("select case when count(c) > 0 then true else false end from MdCustomer c where c.code = :code and c.id <> :id")
    boolean existsByCodeAndIdNot(@Param("code") String code, @Param("id") Long id);

    @Query("select c from MdCustomer c where :keyword is null or :keyword = '' or c.name like %:keyword% or c.code like %:keyword% order by c.id desc")
    Page<MdCustomer> search(@Param("keyword") String keyword, Pageable pageable);

    List<MdCustomer> findAllByStatusOrderByIdAsc(String status);
}
