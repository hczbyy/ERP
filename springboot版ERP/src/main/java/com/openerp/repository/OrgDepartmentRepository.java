package com.openerp.repository;

import com.openerp.entity.OrgDepartment;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface OrgDepartmentRepository extends JpaRepository<OrgDepartment, Long> {
    List<OrgDepartment> findAllByOrderByIdAsc();

    boolean existsByCode(String code);

    @Query("select case when count(d) > 0 then true else false end from OrgDepartment d where d.code = :code and d.id <> :id")
    boolean existsByCodeAndIdNot(@Param("code") String code, @Param("id") Long id);
}
