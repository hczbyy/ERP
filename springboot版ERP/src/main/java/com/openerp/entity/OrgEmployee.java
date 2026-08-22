package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDate;

@Entity
@Table(name = "org_employee")
@Getter
@Setter
public class OrgEmployee extends BaseEntity {
    @Column(name = "emp_no", length = 20, unique = true, nullable = false)
    private String empNo;

    @Column(name = "name", length = 50, nullable = false)
    private String name;

    @Column(name = "gender", length = 10)
    private String gender;

    @Column(name = "phone", length = 20)
    private String phone;

    @Column(name = "email", length = 100)
    private String email;

    @Column(name = "hire_date")
    private LocalDate hireDate;

    @Column(name = "position", length = 50)
    private String position;

    @Column(name = "status", length = 10, nullable = false)
    private String status = "active";

    @Column(name = "department_id")
    private Long departmentId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "department_id", insertable = false, updatable = false)
    private OrgDepartment department;
}
