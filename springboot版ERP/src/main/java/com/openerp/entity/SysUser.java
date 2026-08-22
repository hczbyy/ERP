package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.util.LinkedHashSet;
import java.util.Set;

@Entity
@Table(name = "sys_user")
@Getter
@Setter
public class SysUser extends BaseEntity {
    @Column(name = "username", length = 50, unique = true, nullable = false)
    private String username;

    @Column(name = "password_hash", length = 256, nullable = false)
    private String passwordHash;

    @Column(name = "display_name", length = 50, nullable = false)
    private String displayName;

    @Column(name = "email", length = 100)
    private String email;

    @Column(name = "phone", length = 20)
    private String phone;

    @Column(name = "is_active")
    private boolean active = true;

    @Column(name = "is_superuser")
    private boolean superuser = false;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(name = "sys_user_roles",
            joinColumns = @JoinColumn(name = "user_id"),
            inverseJoinColumns = @JoinColumn(name = "role_id"))
    private Set<SysRole> roles = new LinkedHashSet<>();
}
