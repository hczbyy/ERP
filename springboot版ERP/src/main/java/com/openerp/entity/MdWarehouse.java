package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "md_warehouse")
@Getter
@Setter
public class MdWarehouse extends BaseEntity {
    @Column(name = "code", length = 20, unique = true, nullable = false)
    private String code;

    @Column(name = "name", length = 50, nullable = false)
    private String name;

    @Column(name = "address", length = 200)
    private String address;

    @Column(name = "manager", length = 50)
    private String manager;

    @Column(name = "status", length = 10, nullable = false)
    private String status = "active";
}
