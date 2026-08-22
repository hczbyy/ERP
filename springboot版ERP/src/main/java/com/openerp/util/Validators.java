package com.openerp.util;

import com.openerp.common.BusinessException;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;

public final class Validators {
    private Validators() {
    }

    public static BigDecimal requireIntQty(BigDecimal qty, Long productId, String label) {
        String prefix = productId == null ? "" : ("商品 #" + productId + " ");
        if (qty == null) throw new BusinessException(prefix + label + "格式不正确");
        BigDecimal v = qty;
        if (v.compareTo(v.setScale(0, RoundingMode.UNNECESSARY)) != 0) {
            throw new BusinessException(prefix + label + "必须为整数");
        }
        if (v.compareTo(BigDecimal.ONE) < 0) {
            throw new BusinessException(prefix + label + "必须大于等于 1");
        }
        return v;
    }

    public static LocalDate parseDate(String value, String fieldName) {
        if (value == null || value.isBlank()) return null;
        try {
            return LocalDate.parse(value.trim());
        } catch (DateTimeParseException e) {
            throw new BusinessException(fieldName + "格式不正确，应为 YYYY-MM-DD");
        }
    }
}
