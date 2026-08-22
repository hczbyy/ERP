package com.openerp.repository;

import com.openerp.entity.OrgEmployee;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OrgEmployeeRepository extends JpaRepository<OrgEmployee, Long> {
    boolean existsByEmpNo(String empNo);

    @Query("select case when count(e) > 0 then true else false end from OrgEmployee e where e.empNo = :empNo and e.id <> :id")
    boolean existsByEmpNoAndIdNot(@Param("empNo") String empNo, @Param("id") Long id);

    @Query("select e from OrgEmployee e where :keyword is null or :keyword = '' or e.name like %:keyword% or e.empNo like %:keyword% order by e.id")
    Page<OrgEmployee> search(@Param("keyword") String keyword, Pageable pageable);
}
