package com.openerp.service;

import com.openerp.common.PageResult;
import com.openerp.entity.*;
import com.openerp.repository.*;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class DashboardService {
    private final SoStockOutRepository stockOutRepository;
    private final SoOrderRepository soOrderRepository;
    private final PoOrderRepository poOrderRepository;
    private final InvStockRepository stockRepository;
    private final FinReceivableRepository receivableRepository;
    private final FinPayableRepository payableRepository;

    public DashboardService(SoStockOutRepository stockOutRepository,
                            SoOrderRepository soOrderRepository,
                            PoOrderRepository poOrderRepository,
                            InvStockRepository stockRepository,
                            FinReceivableRepository receivableRepository,
                            FinPayableRepository payableRepository) {
        this.stockOutRepository = stockOutRepository;
        this.soOrderRepository = soOrderRepository;
        this.poOrderRepository = poOrderRepository;
        this.stockRepository = stockRepository;
        this.receivableRepository = receivableRepository;
        this.payableRepository = payableRepository;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> summary() {
        LocalDateTime start = LocalDate.now().atStartOfDay();
        LocalDateTime end = start.plusDays(1);
        double todaySales = stockOutRepository.findAll().stream()
                .filter(o -> o.getCreatedAt() != null
                        && !o.getCreatedAt().isBefore(start) && o.getCreatedAt().isBefore(end))
                .map(SoStockOut::getTotalAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .doubleValue();
        long todayOrders = soOrderRepository.findAll().stream()
                .filter(o -> o.getCreatedAt() != null
                        && !o.getCreatedAt().isBefore(start) && o.getCreatedAt().isBefore(end))
                .count();
        long pendingApprove = poOrderRepository.countByStatus("draft")
                + soOrderRepository.countByStatus("draft");
        long lowStocks = stockRepository.countLowStock();

        double receivableBalance = receivableRepository.findAll().stream()
                .filter(r -> !"settled".equals(r.getStatus()))
                .map(r -> r.getTotalAmount().subtract(r.getReceivedAmount()))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .doubleValue();
        double payableBalance = payableRepository.findAll().stream()
                .filter(p -> !"settled".equals(p.getStatus()))
                .map(p -> p.getTotalAmount().subtract(p.getPaidAmount()))
                .reduce(BigDecimal.ZERO, BigDecimal::add)
                .doubleValue();

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("today_sales", todaySales);
        data.put("today_orders", todayOrders);
        data.put("pending_approve", pendingApprove);
        data.put("low_stocks", lowStocks);
        data.put("receivable_balance", receivableBalance);
        data.put("payable_balance", payableBalance);
        return data;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> salesTrend(int days) {
        days = Math.max(1, Math.min(days, 365));
        LocalDate today = LocalDate.now();
        LocalDate start = today.minusDays(days - 1L);
        Map<LocalDate, Double> amountMap = new LinkedHashMap<>();
        Map<LocalDate, Long> countMap = new LinkedHashMap<>();
        for (SoStockOut o : stockOutRepository.findAll()) {
            LocalDate d = o.getCreatedAt().toLocalDate();
            if (!d.isBefore(start) && !d.isAfter(today)) {
                amountMap.merge(d, o.getTotalAmount().doubleValue(), Double::sum);
            }
        }
        for (SoOrder o : soOrderRepository.findAll()) {
            LocalDate d = o.getCreatedAt().toLocalDate();
            if (!d.isBefore(start) && !d.isAfter(today)) {
                countMap.merge(d, 1L, Long::sum);
            }
        }
        List<String> labels = new ArrayList<>();
        List<Double> amounts = new ArrayList<>();
        List<Long> counts = new ArrayList<>();
        for (int i = 0; i < days; i++) {
            LocalDate d = start.plusDays(i);
            labels.add(d.toString());
            amounts.add(amountMap.getOrDefault(d, 0.0));
            counts.add(countMap.getOrDefault(d, 0L));
        }
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("labels", labels);
        data.put("amounts", amounts);
        data.put("counts", counts);
        return data;
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> topProducts(int limit) {
        limit = Math.max(1, Math.min(limit, 100));
        Map<Long, Map<String, Object>> agg = new LinkedHashMap<>();
        for (SoStockOut so : stockOutRepository.findAll()) {
            for (SoStockOutItem it : so.getItems()) {
                Map<String, Object> row = agg.computeIfAbsent(it.getProductId(), k -> {
                    Map<String, Object> m = new LinkedHashMap<>();
                    m.put("name", it.getProduct() == null ? null : it.getProduct().getName());
                    m.put("qty", 0.0);
                    m.put("amount", 0.0);
                    return m;
                });
                row.put("qty", (double) row.get("qty") + it.getQty().doubleValue());
                row.put("amount", (double) row.get("amount") + it.getAmount().doubleValue());
            }
        }
        return agg.values().stream()
                .sorted((a, b) -> Double.compare((double) b.get("qty"), (double) a.get("qty")))
                .limit(limit)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> lowStocks(int limit) {
        limit = Math.max(1, Math.min(limit, 100));
        return stockRepository.findLowStocks(PageRequest.of(0, limit)).stream().map(row -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("code", row[0]);
            m.put("name", row[1]);
            m.put("qty", ((BigDecimal) row[2]).doubleValue());
            m.put("safety_stock", ((BigDecimal) row[3]).doubleValue());
            return m;
        }).toList();
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> recentOrders(int limit) {
        limit = Math.max(1, Math.min(limit, 100));
        return soOrderRepository.findRecent(PageRequest.of(0, limit)).stream().map(o -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("order_no", o.getOrderNo());
            m.put("customer_name", o.getCustomer() == null ? null : o.getCustomer().getName());
            m.put("total_amount", o.getTotalAmount());
            m.put("status", o.getStatus());
            m.put("created_at", o.getCreatedAt());
            return m;
        }).toList();
    }
}
