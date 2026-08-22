package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "md_category")
@Getter
@Setter
public class MdCategory extends BaseEntity {
    @Column(name = "name", length = 50, unique = true, nullable = false)
    private String name;

    @Column(name = "parent_id")
    private Long parentId;

    @Column(name = "sort")
    private int sort = 0;
}
