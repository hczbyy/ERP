package com.openerp.audit;

import com.openerp.entity.AuditLog;
import com.openerp.repository.AuditLogRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Map;

@Service
public class AuditService {
    private final AuditLogRepository auditLogRepository;
    private final ObjectMapper objectMapper;

    public AuditService(AuditLogRepository auditLogRepository, ObjectMapper objectMapper) {
        this.auditLogRepository = auditLogRepository;
        this.objectMapper = objectMapper;
    }

    public void write(String username, String action, String module,
                      String target, Map<String, Object> detail, String ip) {
        AuditLog log = new AuditLog();
        log.setUsername(username);
        log.setAction(action);
        log.setModule(module);
        log.setTarget(target);
        if (detail != null && !detail.isEmpty()) {
            try {
                log.setDetail(objectMapper.writeValueAsString(detail));
            } catch (JsonProcessingException e) {
                log.setDetail(String.valueOf(detail));
            }
        }
        log.setIp(ip);
        log.setCreatedAt(LocalDateTime.now());
        auditLogRepository.save(log);
    }
}
