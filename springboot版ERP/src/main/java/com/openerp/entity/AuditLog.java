package com.openerp.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;

import java.time.LocalDateTime;

@Entity
@Table(name = "sys_audit_log")
@Getter
@Setter
public class AuditLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "username", length = 50, nullable = false)
    private String username;

    @Column(name = "action", length = 30, nullable = false)
    private String action;

    @Column(name = "module", length = 50, nullable = false)
    private String module;

    @Column(name = "target", length = 100)
    private String target;

    @Column(name = "detail", columnDefinition = "TEXT")
    private String detail;

    @Column(name = "ip", length = 50)
    private String ip;

    @Column(name = "created_at", length = 30)
    private LocalDateTime createdAt;
}
