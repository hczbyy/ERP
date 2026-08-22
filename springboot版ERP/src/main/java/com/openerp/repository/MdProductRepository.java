package com.openerp.repository;

import com.openerp.entity.MdProduct;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;

public interface MdProductRepository extends JpaRepository<MdProduct, Long> {
    boolean existsByCode(String code);

    @Query("select case when count(p) > 0 then true else false end from MdProduct p where p.code = :code and p.id <> :id")
    boolean existsByCodeAndIdNot(@Param("code") String code, @Param("id") Long id);

    @Query("select p from MdProduct p left join fetch p.category where (:keyword is null or :keyword = '' or p.name like %:keyword% or p.code like %:keyword%) and (:categoryId is null or p.categoryId = :categoryId) order by p.id desc")
    Page<MdProduct> search(@Param("keyword") String keyword, @Param("categoryId") Long categoryId, Pageable pageable);

    @Query("select p from MdProduct p left join fetch p.category where (:status is null or :status = '' or p.status = :status) order by p.id")
    List<MdProduct> findAllWithCategory(@Param("status") String status);

    @Query("select p from MdProduct p left join fetch p.category where p.id = :id")
    Optional<MdProduct> findWithCategoryById(@Param("id") Long id);
}
