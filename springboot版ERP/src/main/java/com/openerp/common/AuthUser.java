package com.openerp.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.Set;

@Getter
@AllArgsConstructor
public class AuthUser {
    private final Long id;
    private final String username;
    private final String displayName;
    private final boolean superuser;
    private final boolean active;
    private final Set<String> permissions;

    public boolean hasPermission(String code) {
        return superuser || permissions.contains(code);
    }
}
