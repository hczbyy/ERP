package com.openerp.repository;

import com.openerp.entity.MdCategory;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MdCategoryRepository extends JpaRepository<MdCategory, Long> {
    List<MdCategory> findAllByOrderBySortAscIdAsc();

    boolean existsByName(String name);

    @Query("select case when count(c) > 0 then true else false end from MdCategory c where c.name = :name and c.id <> :id")
    boolean existsByNameAndIdNot(@Param("name") String name, @Param("id") Long id);
}
