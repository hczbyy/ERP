package com.openerp.service;

import com.openerp.audit.AuditService;
import com.openerp.common.BusinessException;
import com.openerp.common.PageResult;
import com.openerp.dto.FinanceRequests;
import com.openerp.entity.*;
import com.openerp.repository.*;
import com.openerp.util.BillNoGenerator;
import com.openerp.util.Rows;
import com.openerp.util.Validators;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.util.Map;
import java.util.List;

@Service
public class FinanceService {
    private final FinReceivableRepository receivableRepository;
    private final FinPayableRepository payableRepository;
    private final FinReceiptRepository receiptRepository;
    private final FinPaymentRepository paymentRepository;
    private final MdCustomerRepository customerRepository;
    private final MdSupplierRepository supplierRepository;
    private final BillNoGenerator billNoGenerator;
    private final AuditService auditService;

    public FinanceService(FinReceivableRepository receivableRepository,
                          FinPayableRepository payableRepository,
                          FinReceiptRepository receiptRepository,
                          FinPaymentRepository paymentRepository,
                          MdCustomerRepository customerRepository,
                          MdSupplierRepository supplierRepository,
                          BillNoGenerator billNoGenerator,
                          AuditService auditService) {
        this.receivableRepository = receivableRepository;
        this.payableRepository = payableRepository;
        this.receiptRepository = receiptRepository;
        this.paymentRepository = paymentRepository;
        this.customerRepository = customerRepository;
        this.supplierRepository = supplierRepository;
        this.billNoGenerator = billNoGenerator;
        this.auditService = auditService;
    }

    private static BigDecimal money(BigDecimal v) {
        return (v == null ? BigDecimal.ZERO : v).setScale(2, RoundingMode.HALF_UP);
    }

    // ---------------- 应收 ----------------

    @Transactional(readOnly = true)
    public PageResult pageReceivables(String status, String keyword, int pageNo, int pageSize) {
        Page<FinReceivable> p = receivableRepository.search(status, keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::receivable).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createReceivable(FinanceRequests.ReceivableCreateBody body,
                                                String username, String ip) {
        if (!customerRepository.existsById(body.customerId())) {
            throw new BusinessException("客户不存在");
        }
        FinReceivable r = new FinReceivable();
        r.setReceivableNo(billNoGenerator.gen("receivable"));
        r.setSourceNo("MANUAL");
        r.setCustomerId(body.customerId());
        r.setTotalAmount(money(body.amount()));
        r.setReceivedAmount(BigDecimal.ZERO);
        r.setStatus("open");
        r.setDueDate(Validators.parseDate(body.dueDate(), "到期日"));
        r.setRemark(body.remark());
        r.setCreatedBy(username);
        receivableRepository.save(r);
        auditService.write(username, "create", "finance", r.getReceivableNo(),
                Map.of("customer_id", body.customerId(), "amount", r.getTotalAmount().toPlainString()), ip);
        return Rows.receivable(r);
    }

    // ---------------- 应付 ----------------

    @Transactional(readOnly = true)
    public PageResult pagePayables(String status, String keyword, int pageNo, int pageSize) {
        Page<FinPayable> p = payableRepository.search(status, keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::payable).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createPayable(FinanceRequests.PayableCreateBody body,
                                             String username, String ip) {
        if (!supplierRepository.existsById(body.supplierId())) {
            throw new BusinessException("供应商不存在");
        }
        FinPayable p = new FinPayable();
        p.setPayableNo(billNoGenerator.gen("payable"));
        p.setSourceNo("MANUAL");
        p.setSupplierId(body.supplierId());
        p.setTotalAmount(money(body.amount()));
        p.setPaidAmount(BigDecimal.ZERO);
        p.setStatus("open");
        p.setDueDate(Validators.parseDate(body.dueDate(), "到期日"));
        p.setRemark(body.remark());
        p.setCreatedBy(username);
        payableRepository.save(p);
        auditService.write(username, "create", "finance", p.getPayableNo(),
                Map.of("supplier_id", body.supplierId(), "amount", p.getTotalAmount().toPlainString()), ip);
        return Rows.payable(p);
    }

    // ---------------- 收款 ----------------

    @Transactional(readOnly = true)
    public PageResult pageReceipts(String keyword, int pageNo, int pageSize) {
        Page<FinReceipt> p = receiptRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::receipt).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createReceipt(FinanceRequests.ReceiptBody body, String username, String ip) {
        FinReceivable receivable = receivableRepository.findById(body.receivableId())
                .orElseThrow(() -> new BusinessException("应收单不存在"));
        BigDecimal amount = money(body.amount());
        BigDecimal balance = money(receivable.getTotalAmount().subtract(receivable.getReceivedAmount()));
        if (amount.signum() <= 0) {
            throw new BusinessException("收款金额必须大于0");
        }
        if (amount.compareTo(balance) > 0) {
            throw new BusinessException("收款金额 " + amount.toPlainString()
                    + " 超过应收余额 " + balance.toPlainString());
        }
        if (body.payMethod() != null && !List.of("cash", "bank", "transfer").contains(body.payMethod())) {
            throw new BusinessException("支付方式必须为 cash / bank / transfer");
        }
        FinReceipt receipt = new FinReceipt();
        receipt.setReceiptNo(billNoGenerator.gen("receipt"));
        receipt.setReceivableId(receivable.getId());
        receipt.setReceivableNo(receivable.getReceivableNo());
        receipt.setCustomerId(receivable.getCustomerId());
        receipt.setAmount(amount);
        receipt.setPayMethod(body.payMethod() == null ? "bank" : body.payMethod());
        LocalDate receivedAt = Validators.parseDate(body.receivedAt(), "收款日期");
        receipt.setReceivedAt(receivedAt == null ? LocalDate.now() : receivedAt);
        receipt.setRemark(body.remark());
        receipt.setCreatedBy(username);
        receiptRepository.save(receipt);

        receivable.setReceivedAmount(money(receivable.getReceivedAmount().add(amount)));
        receivable.setStatus(receivable.getReceivedAmount().compareTo(receivable.getTotalAmount()) >= 0
                ? "settled" : "partial");
        receivableRepository.save(receivable);
        auditService.write(username, "pay", "finance", receipt.getReceiptNo(),
                Map.of("receivable_no", receipt.getReceivableNo(), "amount", amount.toPlainString()), ip);
        return Map.of("receipt_no", receipt.getReceiptNo());
    }

    // ---------------- 付款 ----------------

    @Transactional(readOnly = true)
    public PageResult pagePayments(String keyword, int pageNo, int pageSize) {
        Page<FinPayment> p = paymentRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::payment).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional
    public Map<String, Object> createPayment(FinanceRequests.PaymentBody body, String username, String ip) {
        FinPayable payable = payableRepository.findById(body.payableId())
                .orElseThrow(() -> new BusinessException("应付单不存在"));
        BigDecimal amount = money(body.amount());
        BigDecimal balance = money(payable.getTotalAmount().subtract(payable.getPaidAmount()));
        if (amount.signum() <= 0) {
            throw new BusinessException("付款金额必须大于0");
        }
        if (amount.compareTo(balance) > 0) {
            throw new BusinessException("付款金额 " + amount.toPlainString()
                    + " 超过应付余额 " + balance.toPlainString());
        }
        if (body.payMethod() != null && !List.of("cash", "bank", "transfer").contains(body.payMethod())) {
            throw new BusinessException("支付方式必须为 cash / bank / transfer");
        }
        FinPayment payment = new FinPayment();
        payment.setPaymentNo(billNoGenerator.gen("payment"));
        payment.setPayableId(payable.getId());
        payment.setPayableNo(payable.getPayableNo());
        payment.setSupplierId(payable.getSupplierId());
        payment.setAmount(amount);
        payment.setPayMethod(body.payMethod() == null ? "bank" : body.payMethod());
        LocalDate paidAt = Validators.parseDate(body.paidAt(), "付款日期");
        payment.setPaidAt(paidAt == null ? LocalDate.now() : paidAt);
        payment.setRemark(body.remark());
        payment.setCreatedBy(username);
        paymentRepository.save(payment);

        payable.setPaidAmount(money(payable.getPaidAmount().add(amount)));
        payable.setStatus(payable.getPaidAmount().compareTo(payable.getTotalAmount()) >= 0
                ? "settled" : "partial");
        payableRepository.save(payable);
        auditService.write(username, "pay", "finance", payment.getPaymentNo(),
                Map.of("payable_no", payment.getPayableNo(), "amount", amount.toPlainString()), ip);
        return Map.of("payment_no", payment.getPaymentNo());
    }

}
