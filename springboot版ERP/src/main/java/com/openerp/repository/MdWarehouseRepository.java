package com.openerp.repository;

import com.openerp.entity.MdWarehouse;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface MdWarehouseRepository extends JpaRepository<MdWarehouse, Long> {
    List<MdWarehouse> findAllByOrderByIdAsc();

    boolean existsByCode(String code);

    @Query("select case when count(w) > 0 then true else false end from MdWarehouse w where w.code = :code and w.id <> :id")
    boolean existsByCodeAndIdNot(@Param("code") String code, @Param("id") Long id);
}
