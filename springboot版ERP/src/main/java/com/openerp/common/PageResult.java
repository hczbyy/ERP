package com.openerp.common;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

@Getter
@AllArgsConstructor
public class PageResult {
    private final List<?> items;
    private final long total;
    private final int page;
    private final int pageSize;
}
