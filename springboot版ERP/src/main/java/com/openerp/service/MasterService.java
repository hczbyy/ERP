package com.openerp.service;

import com.openerp.audit.AuditService;
import com.openerp.common.BusinessException;
import com.openerp.common.PageResult;
import com.openerp.dto.MasterRequests;
import com.openerp.entity.*;
import com.openerp.repository.*;
import com.openerp.util.Rows;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Service
public class MasterService {
    private static final String PRODUCTS_ALL_CACHE = "erp:cache:products:all";

    private final MdCategoryRepository categoryRepository;
    private final MdProductRepository productRepository;
    private final MdCustomerRepository customerRepository;
    private final MdSupplierRepository supplierRepository;
    private final MdWarehouseRepository warehouseRepository;
    private final PoOrderRepository poOrderRepository;
    private final SoOrderRepository soOrderRepository;
    private final InvStockRepository stockRepository;
    private final PoOrderItemRepository poOrderItemRepository;
    private final SoOrderItemRepository soOrderItemRepository;
    private final AuditService auditService;
    private final RedisTemplate<String, Object> redisTemplate;

    public MasterService(MdCategoryRepository categoryRepository,
                         MdProductRepository productRepository,
                         MdCustomerRepository customerRepository,
                         MdSupplierRepository supplierRepository,
                         MdWarehouseRepository warehouseRepository,
                         PoOrderRepository poOrderRepository,
                         SoOrderRepository soOrderRepository,
                         InvStockRepository stockRepository,
                         PoOrderItemRepository poOrderItemRepository,
                         SoOrderItemRepository soOrderItemRepository,
                         AuditService auditService,
                         RedisTemplate<String, Object> redisTemplate) {
        this.categoryRepository = categoryRepository;
        this.productRepository = productRepository;
        this.customerRepository = customerRepository;
        this.supplierRepository = supplierRepository;
        this.warehouseRepository = warehouseRepository;
        this.poOrderRepository = poOrderRepository;
        this.soOrderRepository = soOrderRepository;
        this.stockRepository = stockRepository;
        this.poOrderItemRepository = poOrderItemRepository;
        this.soOrderItemRepository = soOrderItemRepository;
        this.auditService = auditService;
        this.redisTemplate = redisTemplate;
    }

    private static PageResult page(Page<?> p, int pageNo, int pageSize) {
        return new PageResult(p.getContent(), p.getTotalElements(), pageNo, pageSize);
    }

    private static void validateStatus(String status) {
        if (status != null && !status.isBlank() && !List.of("active", "disabled").contains(status)) {
            throw new BusinessException("状态必须为 active 或 disabled");
        }
    }

    // ---------------- 商品分类 ----------------

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listCategories() {
        return categoryRepository.findAllByOrderBySortAscIdAsc().stream().map(Rows::category).toList();
    }

    @Transactional
    public Map<String, Object> createCategory(MasterRequests.CategoryBody body, String username, String ip) {
        if (categoryRepository.existsByName(body.name())) {
            throw new BusinessException("分类 " + body.name() + " 已存在");
        }
        MdCategory c = new MdCategory();
        c.setName(body.name());
        c.setSort(body.sort());
        categoryRepository.save(c);
        auditService.write(username, "create", "master", "分类 " + body.name(), null, ip);
        return Map.of("id", c.getId());
    }

    @Transactional
    public void updateCategory(Long id, MasterRequests.CategoryBody body, String username, String ip) {
        MdCategory c = categoryRepository.findById(id)
                .orElseThrow(() -> new BusinessException("分类不存在"));
        if (categoryRepository.existsByNameAndIdNot(body.name(), id)) {
            throw new BusinessException("分类 " + body.name() + " 已存在");
        }
        c.setName(body.name());
        c.setSort(body.sort());
        categoryRepository.save(c);
        auditService.write(username, "update", "master", "分类 " + body.name(), null, ip);
    }

    @Transactional
    public void deleteCategory(Long id, String username, String ip) {
        MdCategory c = categoryRepository.findById(id)
                .orElseThrow(() -> new BusinessException("分类不存在"));
        if (productRepository.findAll().stream().anyMatch(p -> id.equals(p.getCategoryId()))) {
            throw new BusinessException("该分类下存在商品，无法删除");
        }
        categoryRepository.delete(c);
        auditService.write(username, "delete", "master", "分类 " + c.getName(), null, ip);
    }

    // ---------------- 商品 ----------------

    @Transactional(readOnly = true)
    public PageResult pageProducts(String keyword, Long categoryId, int pageNo, int pageSize) {
        Page<MdProduct> p = productRepository.search(keyword, categoryId,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        List<Map<String, Object>> items = p.getContent().stream().map(Rows::product).toList();
        return new PageResult(items, p.getTotalElements(), pageNo, pageSize);
    }

    @SuppressWarnings("unchecked")
    @Transactional(readOnly = true)
    public List<Map<String, Object>> allProducts(String status) {
        String cacheKey = PRODUCTS_ALL_CACHE + ":" + (status == null ? "" : status);
        Object cached = null;
        try {
            cached = redisTemplate.opsForValue().get(cacheKey);
        } catch (Exception ignored) {
        }
        if (cached instanceof List<?> list && !list.isEmpty()) {
            return (List<Map<String, Object>>) list;
        }
        List<Map<String, Object>> rows = productRepository.findAllWithCategory(status).stream()
                .map(Rows::product).toList();
        try {
            redisTemplate.opsForValue().set(cacheKey, rows, Duration.ofSeconds(60));
        } catch (Exception ignored) {
        }
        return rows;
    }

    @Transactional
    public Map<String, Object> createProduct(MasterRequests.ProductBody body, String username, String ip) {
        if (body.categoryId() != null && !categoryRepository.existsById(body.categoryId())) {
            throw new BusinessException("商品分类不存在");
        }
        if (productRepository.existsByCode(body.code())) {
            throw new BusinessException("商品编码 " + body.code() + " 已存在");
        }
        MdProduct p = new MdProduct();
        fillProduct(p, body);
        productRepository.save(p);
        evictProductsCache();
        auditService.write(username, "create", "master", "商品 " + body.name(), null, ip);
        return Map.of("id", p.getId());
    }

    @Transactional
    public void updateProduct(Long id, MasterRequests.ProductBody body, String username, String ip) {
        MdProduct p = productRepository.findById(id)
                .orElseThrow(() -> new BusinessException("商品不存在"));
        if (body.categoryId() != null && !categoryRepository.existsById(body.categoryId())) {
            throw new BusinessException("商品分类不存在");
        }
        if (productRepository.existsByCodeAndIdNot(body.code(), id)) {
            throw new BusinessException("商品编码 " + body.code() + " 已存在");
        }
        fillProduct(p, body);
        productRepository.save(p);
        evictProductsCache();
        auditService.write(username, "update", "master", "商品 " + body.name(), null, ip);
    }

    private void fillProduct(MdProduct p, MasterRequests.ProductBody body) {
        validateStatus(body.status());
        p.setCode(body.code());
        p.setName(body.name());
        p.setSpec(body.spec());
        p.setUnit(body.unit() == null || body.unit().isBlank() ? "件" : body.unit());
        p.setBarcode(body.barcode());
        p.setCategoryId(body.categoryId());
        p.setPurchasePrice(nz(body.purchasePrice()));
        p.setSalePrice(nz(body.salePrice()));
        p.setSafetyStock(nz(body.safetyStock()));
        p.setStatus(body.status() == null || body.status().isBlank() ? "active" : body.status());
        p.setDescription(body.description());
    }

    private static BigDecimal nz(BigDecimal v) {
        return v == null ? BigDecimal.ZERO : v;
    }

    @Transactional
    public void deleteProduct(Long id, String username, String ip) {
        MdProduct p = productRepository.findById(id)
                .orElseThrow(() -> new BusinessException("商品不存在"));
        if (poOrderItemRepository.existsByProductId(id)
                || soOrderItemRepository.existsByProductId(id)
                || stockRepository.findAll().stream().anyMatch(s -> id.equals(s.getProductId()))) {
            throw new BusinessException("商品已发生业务单据或存在库存，请改为停用");
        }
        productRepository.delete(p);
        evictProductsCache();
        auditService.write(username, "delete", "master", "商品 " + p.getName(), null, ip);
    }

    private void evictProductsCache() {
        try {
            var keys = redisTemplate.keys(PRODUCTS_ALL_CACHE + ":*");
            if (keys != null) redisTemplate.delete(keys);
        } catch (Exception ignored) {
        }
    }

    // ---------------- 客户 ----------------

    @Transactional(readOnly = true)
    public PageResult pageCustomers(String keyword, int pageNo, int pageSize) {
        Page<MdCustomer> p = customerRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::customer).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> allCustomers(String status) {
        return customerRepository.findAllByStatusOrderByIdAsc(status).stream().map(Rows::customer).toList();
    }

    @Transactional
    public Map<String, Object> createCustomer(MasterRequests.CustomerBody body, String username, String ip) {
        if (customerRepository.existsByCode(body.code())) {
            throw new BusinessException("客户编码 " + body.code() + " 已存在");
        }
        validateStatus(body.status());
        MdCustomer c = new MdCustomer();
        fillCustomer(c, body);
        customerRepository.save(c);
        auditService.write(username, "create", "master", "客户 " + body.name(), null, ip);
        return Map.of("id", c.getId());
    }

    @Transactional
    public void updateCustomer(Long id, MasterRequests.CustomerBody body, String username, String ip) {
        MdCustomer c = customerRepository.findById(id)
                .orElseThrow(() -> new BusinessException("客户不存在"));
        if (customerRepository.existsByCodeAndIdNot(body.code(), id)) {
            throw new BusinessException("客户编码 " + body.code() + " 已存在");
        }
        validateStatus(body.status());
        fillCustomer(c, body);
        customerRepository.save(c);
        auditService.write(username, "update", "master", "客户 " + body.name(), null, ip);
    }

    private void fillCustomer(MdCustomer c, MasterRequests.CustomerBody body) {
        c.setCode(body.code());
        c.setName(body.name());
        c.setContact(body.contact());
        c.setPhone(body.phone());
        c.setAddress(body.address());
        c.setCreditLimit(nz(body.creditLimit()));
        c.setStatus(body.status() == null || body.status().isBlank() ? "active" : body.status());
    }

    @Transactional
    public void deleteCustomer(Long id, String username, String ip) {
        MdCustomer c = customerRepository.findById(id)
                .orElseThrow(() -> new BusinessException("客户不存在"));
        if (soOrderRepository.findAll().stream().anyMatch(o -> id.equals(o.getCustomerId()))) {
            throw new BusinessException("该客户存在销售单据，请改为停用");
        }
        customerRepository.delete(c);
        auditService.write(username, "delete", "master", "客户 " + c.getName(), null, ip);
    }

    // ---------------- 供应商 ----------------

    @Transactional(readOnly = true)
    public PageResult pageSuppliers(String keyword, int pageNo, int pageSize) {
        Page<MdSupplier> p = supplierRepository.search(keyword,
                PageRequest.of(Math.max(1, pageNo) - 1, Math.min(Math.max(1, pageSize), 100)));
        return new PageResult(p.getContent().stream().map(Rows::supplier).toList(),
                p.getTotalElements(), pageNo, pageSize);
    }

    @Transactional(readOnly = true)
    public List<Map<String, Object>> allSuppliers(String status) {
        return supplierRepository.findAllByStatusOrderByIdAsc(status).stream().map(Rows::supplier).toList();
    }

    @Transactional
    public Map<String, Object> createSupplier(MasterRequests.SupplierBody body, String username, String ip) {
        if (supplierRepository.existsByCode(body.code())) {
            throw new BusinessException("供应商编码 " + body.code() + " 已存在");
        }
        validateStatus(body.status());
        MdSupplier s = new MdSupplier();
        fillSupplier(s, body);
        supplierRepository.save(s);
        auditService.write(username, "create", "master", "供应商 " + body.name(), null, ip);
        return Map.of("id", s.getId());
    }

    @Transactional
    public void updateSupplier(Long id, MasterRequests.SupplierBody body, String username, String ip) {
        MdSupplier s = supplierRepository.findById(id)
                .orElseThrow(() -> new BusinessException("供应商不存在"));
        if (supplierRepository.existsByCodeAndIdNot(body.code(), id)) {
            throw new BusinessException("供应商编码 " + body.code() + " 已存在");
        }
        validateStatus(body.status());
        fillSupplier(s, body);
        supplierRepository.save(s);
        auditService.write(username, "update", "master", "供应商 " + body.name(), null, ip);
    }

    private void fillSupplier(MdSupplier s, MasterRequests.SupplierBody body) {
        s.setCode(body.code());
        s.setName(body.name());
        s.setContact(body.contact());
        s.setPhone(body.phone());
        s.setAddress(body.address());
        s.setStatus(body.status() == null || body.status().isBlank() ? "active" : body.status());
    }

    @Transactional
    public void deleteSupplier(Long id, String username, String ip) {
        MdSupplier s = supplierRepository.findById(id)
                .orElseThrow(() -> new BusinessException("供应商不存在"));
        if (poOrderRepository.findAll().stream().anyMatch(o -> id.equals(o.getSupplierId()))) {
            throw new BusinessException("该供应商存在采购单据，请改为停用");
        }
        supplierRepository.delete(s);
        auditService.write(username, "delete", "master", "供应商 " + s.getName(), null, ip);
    }

    // ---------------- 仓库 ----------------

    @Transactional(readOnly = true)
    public List<Map<String, Object>> listWarehouses() {
        return warehouseRepository.findAllByOrderByIdAsc().stream().map(Rows::warehouse).toList();
    }

    @Transactional
    public Map<String, Object> createWarehouse(MasterRequests.WarehouseBody body, String username, String ip) {
        if (warehouseRepository.existsByCode(body.code())) {
            throw new BusinessException("仓库编码 " + body.code() + " 已存在");
        }
        validateStatus(body.status());
        MdWarehouse w = new MdWarehouse();
        fillWarehouse(w, body);
        warehouseRepository.save(w);
        auditService.write(username, "create", "master", "仓库 " + body.name(), null, ip);
        return Map.of("id", w.getId());
    }

    @Transactional
    public void updateWarehouse(Long id, MasterRequests.WarehouseBody body, String username, String ip) {
        MdWarehouse w = warehouseRepository.findById(id)
                .orElseThrow(() -> new BusinessException("仓库不存在"));
        if (warehouseRepository.existsByCodeAndIdNot(body.code(), id)) {
            throw new BusinessException("仓库编码 " + body.code() + " 已存在");
        }
        validateStatus(body.status());
        fillWarehouse(w, body);
        warehouseRepository.save(w);
        auditService.write(username, "update", "master", "仓库 " + body.name(), null, ip);
    }

    private void fillWarehouse(MdWarehouse w, MasterRequests.WarehouseBody body) {
        w.setCode(body.code());
        w.setName(body.name());
        w.setAddress(body.address());
        w.setManager(body.manager());
        w.setStatus(body.status() == null || body.status().isBlank() ? "active" : body.status());
    }

    @Transactional
    public void deleteWarehouse(Long id, String username, String ip) {
        MdWarehouse w = warehouseRepository.findById(id)
                .orElseThrow(() -> new BusinessException("仓库不存在"));
        if (stockRepository.existsByWarehouseId(id)) {
            throw new BusinessException("该仓库存在库存记录，无法删除");
        }
        warehouseRepository.delete(w);
        auditService.write(username, "delete", "master", "仓库 " + w.getName(), null, ip);
    }
}
