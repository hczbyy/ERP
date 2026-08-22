package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

@Entity
@Table(name = "org_department")
@Getter
@Setter
public class OrgDepartment extends BaseEntity {
    @Column(name = "code", length = 20, unique = true, nullable = false)
    private String code;

    @Column(name = "name", length = 50, nullable = false)
    private String name;

    @Column(name = "leader", length = 50)
    private String leader;

    @Column(name = "phone", length = 20)
    private String phone;

    @Column(name = "remark", length = 200)
    private String remark;
}
