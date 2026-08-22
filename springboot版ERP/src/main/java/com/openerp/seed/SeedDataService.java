package com.openerp.seed;

import com.openerp.entity.*;
import com.openerp.repository.*;
import com.openerp.service.InventoryService;
import com.openerp.util.PasswordUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

@Service
public class SeedDataService {
    private static final Logger log = LoggerFactory.getLogger(SeedDataService.class);

    private final SysUserRepository userRepository;
    private final SysRoleRepository roleRepository;
    private final SysPermissionRepository permissionRepository;
    private final OrgDepartmentRepository departmentRepository;
    private final OrgEmployeeRepository employeeRepository;
    private final MdCategoryRepository categoryRepository;
    private final MdProductRepository productRepository;
    private final MdCustomerRepository customerRepository;
    private final MdSupplierRepository supplierRepository;
    private final MdWarehouseRepository warehouseRepository;
    private final InventoryService inventoryService;

    public SeedDataService(SysUserRepository userRepository,
                           SysRoleRepository roleRepository,
                           SysPermissionRepository permissionRepository,
                           OrgDepartmentRepository departmentRepository,
                           OrgEmployeeRepository employeeRepository,
                           MdCategoryRepository categoryRepository,
                           MdProductRepository productRepository,
                           MdCustomerRepository customerRepository,
                           MdSupplierRepository supplierRepository,
                           MdWarehouseRepository warehouseRepository,
                           InventoryService inventoryService) {
        this.userRepository = userRepository;
        this.roleRepository = roleRepository;
        this.permissionRepository = permissionRepository;
        this.departmentRepository = departmentRepository;
        this.employeeRepository = employeeRepository;
        this.categoryRepository = categoryRepository;
        this.productRepository = productRepository;
        this.customerRepository = customerRepository;
        this.supplierRepository = supplierRepository;
        this.warehouseRepository = warehouseRepository;
        this.inventoryService = inventoryService;
    }

    @Transactional
    public void seedIfEmpty() {
        if (userRepository.count() > 0) return;

        // 1. 权限点
        Map<String, SysPermission> permMap = new HashMap<>();
        for (Object[] row : new Object[][]{
                {"dashboard", "dashboard:view", "查看仪表盘"},
                {"master", "master:product:read", "商品查询"},
                {"master", "master:product:manage", "商品管理"},
                {"master", "master:customer:read", "客户查询"},
                {"master", "master:customer:manage", "客户管理"},
                {"master", "master:supplier:read", "供应商查询"},
                {"master", "master:supplier:manage", "供应商管理"},
                {"master", "master:warehouse:read", "仓库查询"},
                {"master", "master:warehouse:manage", "仓库管理"},
                {"purchase", "purchase:order:read", "采购单查询"},
                {"purchase", "purchase:order:manage", "采购单管理(含审核)"},
                {"purchase", "purchase:receive:manage", "采购收货"},
                {"sales", "sales:order:read", "销售单查询"},
                {"sales", "sales:order:manage", "销售单管理(含审核)"},
                {"sales", "sales:ship:manage", "销售发货"},
                {"inventory", "inventory:stock:read", "库存查询"},
                {"inventory", "inventory:manage", "盘点与调拨"},
                {"finance", "finance:read", "财务查询"},
                {"finance", "finance:manage", "收付款核销"},
                {"system", "system:user:manage", "用户管理"},
                {"system", "system:role:manage", "角色管理"},
                {"system", "system:org:manage", "组织架构管理"},
                {"system", "system:audit:read", "审计日志查看"},
        }) {
            SysPermission perm = new SysPermission();
            perm.setModule((String) row[0]);
            perm.setCode((String) row[1]);
            perm.setName((String) row[2]);
            permissionRepository.save(perm);
            permMap.put(perm.getCode(), perm);
        }

        // 2. 内置角色
        Map<String, SysRole> roleMap = new HashMap<>();
        for (Object[] r : new Object[][]{
                {"purchaser", "采购经理", "负责采购下单、审核与收货",
                        new String[]{"dashboard:view", "master:product:read", "master:customer:read",
                                "master:supplier:read", "master:supplier:manage", "master:warehouse:read",
                                "purchase:order:read", "purchase:order:manage", "purchase:receive:manage",
                                "inventory:stock:read", "finance:read"}},
                {"salesperson", "销售经理", "负责销售下单、审核与发货",
                        new String[]{"dashboard:view", "master:product:read", "master:customer:read",
                                "master:customer:manage", "master:warehouse:read",
                                "sales:order:read", "sales:order:manage", "sales:ship:manage",
                                "inventory:stock:read", "finance:read"}},
                {"keeper", "仓管员", "负责库存查询、盘点、调拨与收发货",
                        new String[]{"dashboard:view", "master:product:read", "master:warehouse:read",
                                "purchase:order:read", "purchase:receive:manage",
                                "sales:order:read", "sales:ship:manage",
                                "inventory:stock:read", "inventory:manage"}},
                {"financer", "财务专员", "负责应收应付与收付款核销",
                        new String[]{"dashboard:view", "master:product:read", "master:customer:read",
                                "master:supplier:read", "purchase:order:read", "sales:order:read",
                                "inventory:stock:read", "finance:read", "finance:manage",
                                "system:audit:read"}},
                {"auditor", "审计员", "只读：查询各业务与审计日志",
                        new String[]{"dashboard:view", "master:product:read", "master:customer:read",
                                "master:supplier:read", "purchase:order:read", "sales:order:read",
                                "inventory:stock:read", "finance:read", "system:audit:read"}},
        }) {
            SysRole role = new SysRole();
            role.setCode((String) r[0]);
            role.setName((String) r[1]);
            role.setDescription((String) r[2]);
            role.setBuiltin(true);
            java.util.Set<SysPermission> perms = new java.util.LinkedHashSet<>();
            for (String code : (String[]) r[3]) perms.add(permMap.get(code));
            role.setPermissions(perms);
            roleRepository.save(role);
            roleMap.put(role.getCode(), role);
        }

        // 3. 演示账号
        for (Object[] u : new Object[][]{
                {"admin", "admin123", "系统管理员", null},
                {"purchaser", "demo123", "王采购", "purchaser"},
                {"sales", "demo123", "李销售", "salesperson"},
                {"keeper", "demo123", "张仓管", "keeper"},
                {"finance", "demo123", "赵财务", "financer"},
                {"auditor", "demo123", "孙审计", "auditor"},
        }) {
            SysUser user = new SysUser();
            user.setUsername((String) u[0]);
            user.setPasswordHash(PasswordUtil.hash((String) u[1]));
            user.setDisplayName((String) u[2]);
            user.setSuperuser(u[3] == null);
            if (u[3] != null) user.setRoles(java.util.Set.of(roleMap.get(u[3])));
            userRepository.save(user);
        }

        // 4. 组织
        Map<String, OrgDepartment> deptMap = new HashMap<>();
        for (Object[] d : new Object[][]{
                {"D01", "总经办", "陈总", "0571-88000001"},
                {"D02", "采购部", "王采购", "0571-88000002"},
                {"D03", "销售部", "李销售", "0571-88000003"},
                {"D04", "仓储部", "张仓管", "0571-88000004"},
                {"D05", "财务部", "赵财务", "0571-88000005"},
                {"D06", "人事行政部", "孙审计", "0571-88000006"},
        }) {
            OrgDepartment dept = new OrgDepartment();
            dept.setCode((String) d[0]);
            dept.setName((String) d[1]);
            dept.setLeader((String) d[2]);
            dept.setPhone((String) d[3]);
            departmentRepository.save(dept);
            deptMap.put(dept.getCode(), dept);
        }
        for (Object[] e : new Object[][]{
                {"E001", "陈总", "男", "13800000001", "ceo@openerp.cn", "2020-01-06", "总经理", "D01"},
                {"E002", "王采购", "男", "13800000002", "wang@openerp.cn", "2020-03-12", "采购经理", "D02"},
                {"E003", "李销售", "女", "13800000003", "li@openerp.cn", "2021-05-20", "销售经理", "D03"},
                {"E004", "张仓管", "男", "13800000004", "zhang@openerp.cn", "2021-07-01", "仓库主管", "D04"},
                {"E005", "赵财务", "女", "13800000005", "zhao@openerp.cn", "2020-09-15", "财务经理", "D05"},
                {"E006", "孙审计", "男", "13800000006", "sun@openerp.cn", "2022-02-28", "审计专员", "D06"},
                {"E007", "刘文员", "女", "13800000007", "liu@openerp.cn", "2022-04-11", "采购专员", "D02"},
                {"E008", "周客服", "女", "13800000008", "zhou@openerp.cn", "2023-01-09", "销售专员", "D03"},
        }) {
            OrgEmployee emp = new OrgEmployee();
            emp.setEmpNo((String) e[0]);
            emp.setName((String) e[1]);
            emp.setGender((String) e[2]);
            emp.setPhone((String) e[3]);
            emp.setEmail((String) e[4]);
            emp.setHireDate(LocalDate.parse((String) e[5]));
            emp.setPosition((String) e[6]);
            emp.setDepartmentId(deptMap.get(e[7]).getId());
            employeeRepository.save(emp);
        }

        // 5. 基础资料
        Map<String, MdCategory> catMap = new HashMap<>();
        for (String name : new String[]{"电子设备", "办公用品", "数码配件", "办公家具", "打印耗材"}) {
            MdCategory c = new MdCategory();
            c.setName(name);
            categoryRepository.save(c);
            catMap.put(name, c);
        }
        Map<String, MdProduct> productMap = new HashMap<>();
        for (Object[] p : new Object[][]{
                {"SKU001", "联想ThinkPad E14 笔记本", "i5-1240P/16G/512G", "台", "电子设备", "4299", "5499", "10"},
                {"SKU002", "戴尔27寸显示器", "U2723QE 4K", "台", "电子设备", "1899", "2599", "8"},
                {"SKU003", "罗技无线鼠标", "M650 静音版", "个", "数码配件", "89", "149", "30"},
                {"SKU004", "机械键盘", "87键 茶轴", "把", "数码配件", "159", "269", "20"},
                {"SKU005", "A4复印纸", "70g 500张/包", "包", "办公用品", "18", "28", "100"},
                {"SKU006", "中性笔", "0.5mm 黑色 12支/盒", "盒", "办公用品", "7.5", "15", "80"},
                {"SKU007", "档案盒", "A4 55mm", "个", "办公用品", "4.5", "9", "60"},
                {"SKU008", "金士顿U盘", "64GB USB3.2", "个", "数码配件", "39", "79", "40"},
                {"SKU009", "移动硬盘", "西数 1TB", "个", "数码配件", "299", "459", "15"},
                {"SKU010", "千兆路由器", "WiFi6 AX3000", "台", "电子设备", "229", "399", "12"},
                {"SKU011", "办公椅", "人体工学 网布", "把", "办公家具", "399", "699", "10"},
                {"SKU012", "铁皮文件柜", "四门 900x400x1850", "组", "办公家具", "550", "899", "5"},
                {"SKU013", "惠普硒鼓", "CF218A 黑色", "支", "打印耗材", "149", "259", "25"},
                {"SKU014", "无线耳机", "主动降噪 蓝牙5.3", "副", "数码配件", "199", "349", "20"},
                {"SKU015", "订书机", "标准型 装订25页", "个", "办公用品", "8", "16", "50"},
        }) {
            MdProduct prod = new MdProduct();
            prod.setCode((String) p[0]);
            prod.setName((String) p[1]);
            prod.setSpec((String) p[2]);
            prod.setUnit((String) p[3]);
            prod.setCategoryId(catMap.get(p[4]).getId());
            prod.setPurchasePrice(new BigDecimal((String) p[5]));
            prod.setSalePrice(new BigDecimal((String) p[6]));
            prod.setSafetyStock(new BigDecimal((String) p[7]));
            productRepository.save(prod);
            productMap.put(prod.getCode(), prod);
        }
        for (Object[] c : new Object[][]{
                {"C001", "杭州云启科技有限公司", "吴经理", "13900001001", "杭州市西湖区文三路100号", "100000"},
                {"C002", "上海睿思贸易有限公司", "郑经理", "13900001002", "上海市浦东新区张江路88号", "80000"},
                {"C003", "北京晨光数码", "冯经理", "13900001003", "北京市海淀区中关村大街27号", "50000"},
                {"C004", "深圳华讯电子", "何经理", "13900001004", "深圳市南山区科技园南区", "120000"},
                {"C005", "广州南沙实业", "罗经理", "13900001005", "广州市南沙区环市大道中", "60000"},
                {"C006", "成都天府商贸", "马经理", "13900001006", "成都市高新区天府三街", "40000"},
        }) {
            MdCustomer customer = new MdCustomer();
            customer.setCode((String) c[0]);
            customer.setName((String) c[1]);
            customer.setContact((String) c[2]);
            customer.setPhone((String) c[3]);
            customer.setAddress((String) c[4]);
            customer.setCreditLimit(new BigDecimal((String) c[5]));
            customerRepository.save(customer);
        }
        for (Object[] s : new Object[][]{
                {"S001", "联想（北京）有限公司", "高经理", "13700002001", "北京市海淀区上地西路6号"},
                {"S002", "戴尔（中国）有限公司", "韩经理", "13700002002", "厦门市火炬高新区信息光电园"},
                {"S003", "深圳源丰电子", "杨经理", "13700002003", "深圳市龙岗区坂田工业园"},
                {"S004", "上海纸品大王有限公司", "秦经理", "13700002004", "上海市嘉定区南翔镇"},
                {"S005", "宁波鼎好办公家具", "许经理", "13700002005", "宁波市鄞州区姜山镇"},
        }) {
            MdSupplier supplier = new MdSupplier();
            supplier.setCode((String) s[0]);
            supplier.setName((String) s[1]);
            supplier.setContact((String) s[2]);
            supplier.setPhone((String) s[3]);
            supplier.setAddress((String) s[4]);
            supplierRepository.save(supplier);
        }
        Map<String, MdWarehouse> whMap = new HashMap<>();
        for (Object[] w : new Object[][]{
                {"W01", "一号仓", "杭州市余杭区物流园区1号", "张仓管"},
                {"W02", "二号仓", "杭州市余杭区物流园区2号", "张仓管"},
        }) {
            MdWarehouse wh = new MdWarehouse();
            wh.setCode((String) w[0]);
            wh.setName((String) w[1]);
            wh.setAddress((String) w[2]);
            wh.setManager((String) w[3]);
            warehouseRepository.save(wh);
            whMap.put(wh.getCode(), wh);
        }

        // 6. 期初库存
        for (Object[] st : new Object[][]{
                {"SKU001", "W01", "25"}, {"SKU002", "W01", "15"}, {"SKU003", "W01", "120"},
                {"SKU004", "W01", "60"}, {"SKU005", "W01", "500"}, {"SKU006", "W01", "300"},
                {"SKU007", "W01", "200"}, {"SKU008", "W01", "150"}, {"SKU009", "W01", "30"},
                {"SKU010", "W01", "45"}, {"SKU011", "W01", "18"}, {"SKU012", "W01", "8"},
                {"SKU013", "W01", "80"}, {"SKU014", "W01", "55"}, {"SKU015", "W01", "160"},
                {"SKU003", "W02", "40"}, {"SKU005", "W02", "200"}, {"SKU008", "W02", "60"},
        }) {
            inventoryService.changeStock(productMap.get(st[0]).getId(), whMap.get(st[1]).getId(),
                    new BigDecimal((String) st[2]), "initial", "SEED", "system", "期初建账");
        }
        log.info("[seed] 初始化完成：权限/角色/账号/基础数据/期初库存");
    }
}
