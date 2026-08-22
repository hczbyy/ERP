package com.openerp.util;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.Map;

@Component
public class BillNoGenerator {
    private static final Map<String, String[]> PREFIXES = Map.ofEntries(
            Map.entry("purchase_order", new String[]{"PO", "po_order", "order_no"}),
            Map.entry("sales_order", new String[]{"SO", "so_order", "order_no"}),
            Map.entry("stock_in", new String[]{"SI", "po_stock_in", "stock_in_no"}),
            Map.entry("stock_out", new String[]{"SOUT", "so_stock_out", "stock_out_no"}),
            Map.entry("stock_check", new String[]{"PC", "inv_stock_check", "check_no"}),
            Map.entry("stock_transfer", new String[]{"TR", "inv_stock_transfer", "transfer_no"}),
            Map.entry("receivable", new String[]{"AR", "fin_receivable", "receivable_no"}),
            Map.entry("payable", new String[]{"AP", "fin_payable", "payable_no"}),
            Map.entry("receipt", new String[]{"RC", "fin_receipt", "receipt_no"}),
            Map.entry("payment", new String[]{"PY", "fin_payment", "payment_no"})
    );

    private final JdbcTemplate jdbcTemplate;

    public BillNoGenerator(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public String gen(String kind) {
        String[] cfg = PREFIXES.get(kind);
        if (cfg == null) throw new IllegalArgumentException("未知单据类型: " + kind);
        String prefix = cfg[0];
        String table = cfg[1];
        String column = cfg[2];
        String today = LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE);
        String fullPrefix = prefix + today;
        String sql = String.format(
                "SELECT MAX(%s) FROM %s WHERE %s LIKE ?", column, table, column);
        String max = jdbcTemplate.query(sql, rs -> {
            if (rs.next()) return rs.getString(1);
            return null;
        }, fullPrefix + "%");
        int seq = 1;
        if (max != null && max.length() >= 3) {
            try {
                seq = Integer.parseInt(max.substring(max.length() - 3)) + 1;
            } catch (NumberFormatException ignored) {
                seq = 1;
            }
        }
        return String.format("%s%03d", fullPrefix, seq);
    }
}
