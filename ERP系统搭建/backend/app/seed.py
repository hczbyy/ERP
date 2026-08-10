"""种子数据：权限点、内置角色、演示账号、基础资料、期初库存。

仅在数据库为空时执行（幂等）。演示账号密码：
  admin     / admin123   （超级管理员）
  purchaser / demo123    （采购经理）
  sales     / demo123    （销售经理）
  keeper    / demo123    （仓管员）
  finance   / demo123    （财务专员）
  auditor   / demo123    （审计员）
"""
from datetime import date
from decimal import Decimal

from .database import SessionLocal
from .models import (
    Customer, Department, Employee, Permission, Product, ProductCategory,
    Role, Stock, Supplier, User, Warehouse,
)
from .services.inventory import change_stock
from .utils.security import PasswordHasher

# 权限点定义：(模块, 编码, 名称)
PERMISSIONS = [
    ("dashboard", "dashboard:view", "查看仪表盘"),
    ("master", "master:product:read", "商品查询"),
    ("master", "master:product:manage", "商品管理"),
    ("master", "master:customer:read", "客户查询"),
    ("master", "master:customer:manage", "客户管理"),
    ("master", "master:supplier:read", "供应商查询"),
    ("master", "master:supplier:manage", "供应商管理"),
    ("master", "master:warehouse:read", "仓库查询"),
    ("master", "master:warehouse:manage", "仓库管理"),
    ("purchase", "purchase:order:read", "采购单查询"),
    ("purchase", "purchase:order:manage", "采购单管理(含审核)"),
    ("purchase", "purchase:receive:manage", "采购收货"),
    ("sales", "sales:order:read", "销售单查询"),
    ("sales", "sales:order:manage", "销售单管理(含审核)"),
    ("sales", "sales:ship:manage", "销售发货"),
    ("inventory", "inventory:stock:read", "库存查询"),
    ("inventory", "inventory:manage", "盘点与调拨"),
    ("finance", "finance:read", "财务查询"),
    ("finance", "finance:manage", "收付款核销"),
    ("system", "system:user:manage", "用户管理"),
    ("system", "system:role:manage", "角色管理"),
    ("system", "system:org:manage", "组织架构管理"),
    ("system", "system:audit:read", "审计日志查看"),
]

# 内置角色：(编码, 名称, 描述, 权限码列表)
ROLES = [
    ("purchaser", "采购经理", "负责采购下单、审核与收货", [
        "dashboard:view", "master:product:read", "master:customer:read",
        "master:supplier:read", "master:supplier:manage", "master:warehouse:read",
        "purchase:order:read", "purchase:order:manage", "purchase:receive:manage",
        "inventory:stock:read", "finance:read",
    ]),
    ("salesperson", "销售经理", "负责销售下单、审核与发货", [
        "dashboard:view", "master:product:read", "master:customer:read",
        "master:customer:manage", "master:warehouse:read",
        "sales:order:read", "sales:order:manage", "sales:ship:manage",
        "inventory:stock:read", "finance:read",
    ]),
    ("keeper", "仓管员", "负责库存查询、盘点、调拨与收发货", [
        "dashboard:view", "master:product:read", "master:warehouse:read",
        "purchase:order:read", "purchase:receive:manage",
        "sales:order:read", "sales:ship:manage",
        "inventory:stock:read", "inventory:manage",
    ]),
    ("financer", "财务专员", "负责应收应付与收付款核销", [
        "dashboard:view", "master:product:read", "master:customer:read",
        "master:supplier:read", "purchase:order:read", "sales:order:read",
        "inventory:stock:read", "finance:read", "finance:manage",
        "system:audit:read",
    ]),
    ("auditor", "审计员", "只读：查询各业务与审计日志", [
        "dashboard:view", "master:product:read", "master:customer:read",
        "master:supplier:read", "purchase:order:read", "sales:order:read",
        "inventory:stock:read", "finance:read", "system:audit:read",
    ]),
]

# 演示账号：(用户名, 密码, 姓名, 角色编码)
USERS = [
    ("admin", "admin123", "系统管理员", None),
    ("purchaser", "demo123", "王采购", "purchaser"),
    ("sales", "demo123", "李销售", "salesperson"),
    ("keeper", "demo123", "张仓管", "keeper"),
    ("finance", "demo123", "赵财务", "financer"),
    ("auditor", "demo123", "孙审计", "auditor"),
]

DEPARTMENTS = [
    ("D01", "总经办", "陈总", "0571-88000001"),
    ("D02", "采购部", "王采购", "0571-88000002"),
    ("D03", "销售部", "李销售", "0571-88000003"),
    ("D04", "仓储部", "张仓管", "0571-88000004"),
    ("D05", "财务部", "赵财务", "0571-88000005"),
    ("D06", "人事行政部", "孙审计", "0571-88000006"),
]

EMPLOYEES = [
    ("E001", "陈总", "男", "13800000001", "ceo@openerp.cn", "2020-01-06", "总经理", "D01"),
    ("E002", "王采购", "男", "13800000002", "wang@openerp.cn", "2020-03-12", "采购经理", "D02"),
    ("E003", "李销售", "女", "13800000003", "li@openerp.cn", "2021-05-20", "销售经理", "D03"),
    ("E004", "张仓管", "男", "13800000004", "zhang@openerp.cn", "2021-07-01", "仓库主管", "D04"),
    ("E005", "赵财务", "女", "13800000005", "zhao@openerp.cn", "2020-09-15", "财务经理", "D05"),
    ("E006", "孙审计", "男", "13800000006", "sun@openerp.cn", "2022-02-28", "审计专员", "D06"),
    ("E007", "刘文员", "女", "13800000007", "liu@openerp.cn", "2022-04-11", "采购专员", "D02"),
    ("E008", "周客服", "女", "13800000008", "zhou@openerp.cn", "2023-01-09", "销售专员", "D03"),
]

CATEGORIES = ["电子设备", "办公用品", "数码配件", "办公家具", "打印耗材"]

# 商品：(编码, 名称, 规格, 单位, 分类, 采购价, 销售价, 安全库存)
PRODUCTS = [
    ("SKU001", "联想ThinkPad E14 笔记本", "i5-1240P/16G/512G", "台", "电子设备", 4299, 5499, 10),
    ("SKU002", "戴尔27寸显示器", "U2723QE 4K", "台", "电子设备", 1899, 2599, 8),
    ("SKU003", "罗技无线鼠标", "M650 静音版", "个", "数码配件", 89, 149, 30),
    ("SKU004", "机械键盘", "87键 茶轴", "把", "数码配件", 159, 269, 20),
    ("SKU005", "A4复印纸", "70g 500张/包", "包", "办公用品", 18, 28, 100),
    ("SKU006", "中性笔", "0.5mm 黑色 12支/盒", "盒", "办公用品", 7.5, 15, 80),
    ("SKU007", "档案盒", "A4 55mm", "个", "办公用品", 4.5, 9, 60),
    ("SKU008", "金士顿U盘", "64GB USB3.2", "个", "数码配件", 39, 79, 40),
    ("SKU009", "移动硬盘", "西数 1TB", "个", "数码配件", 299, 459, 15),
    ("SKU010", "千兆路由器", "WiFi6 AX3000", "台", "电子设备", 229, 399, 12),
    ("SKU011", "办公椅", "人体工学 网布", "把", "办公家具", 399, 699, 10),
    ("SKU012", "铁皮文件柜", "四门 900x400x1850", "组", "办公家具", 550, 899, 5),
    ("SKU013", "惠普硒鼓", "CF218A 黑色", "支", "打印耗材", 149, 259, 25),
    ("SKU014", "无线耳机", "主动降噪 蓝牙5.3", "副", "数码配件", 199, 349, 20),
    ("SKU015", "订书机", "标准型 装订25页", "个", "办公用品", 8, 16, 50),
]

CUSTOMERS = [
    ("C001", "杭州云启科技有限公司", "吴经理", "13900001001", "杭州市西湖区文三路100号", 100000),
    ("C002", "上海睿思贸易有限公司", "郑经理", "13900001002", "上海市浦东新区张江路88号", 80000),
    ("C003", "北京晨光数码", "冯经理", "13900001003", "北京市海淀区中关村大街27号", 50000),
    ("C004", "深圳华讯电子", "何经理", "13900001004", "深圳市南山区科技园南区", 120000),
    ("C005", "广州南沙实业", "罗经理", "13900001005", "广州市南沙区环市大道中", 60000),
    ("C006", "成都天府商贸", "马经理", "13900001006", "成都市高新区天府三街", 40000),
]

SUPPLIERS = [
    ("S001", "联想（北京）有限公司", "高经理", "13700002001", "北京市海淀区上地西路6号"),
    ("S002", "戴尔（中国）有限公司", "韩经理", "13700002002", "厦门市火炬高新区信息光电园"),
    ("S003", "深圳源丰电子", "杨经理", "13700002003", "深圳市龙岗区坂田工业园"),
    ("S004", "上海纸品大王有限公司", "秦经理", "13700002004", "上海市嘉定区南翔镇"),
    ("S005", "宁波鼎好办公家具", "许经理", "13700002005", "宁波市鄞州区姜山镇"),
]

WAREHOUSES = [
    ("W01", "一号仓", "杭州市余杭区物流园区1号", "张仓管"),
    ("W02", "二号仓", "杭州市余杭区物流园区2号", "张仓管"),
]

# 期初库存：(商品编码, 仓库编码, 数量)
INITIAL_STOCKS = [
    ("SKU001", "W01", 25), ("SKU002", "W01", 15), ("SKU003", "W01", 120),
    ("SKU004", "W01", 60), ("SKU005", "W01", 500), ("SKU006", "W01", 300),
    ("SKU007", "W01", 200), ("SKU008", "W01", 150), ("SKU009", "W01", 30),
    ("SKU010", "W01", 45), ("SKU011", "W01", 18), ("SKU012", "W01", 8),
    ("SKU013", "W01", 80), ("SKU014", "W01", 55), ("SKU015", "W01", 160),
    ("SKU003", "W02", 40), ("SKU005", "W02", 200), ("SKU008", "W02", 60),
]


def seed_if_empty() -> None:
    db = SessionLocal()
    try:
        if db.query(User).first():
            return  # 已有数据，跳过

        # 1. 权限点
        perm_map = {}
        for module, code, name in PERMISSIONS:
            p = Permission(code=code, name=name, module=module)
            db.add(p)
            perm_map[code] = p
        db.flush()

        # 2. 内置角色
        role_map = {}
        for code, name, desc, perms in ROLES:
            r = Role(code=code, name=name, description=desc, is_builtin=True)
            r.permissions = [perm_map[c] for c in perms]
            db.add(r)
            role_map[code] = r

        # 3. 用户
        for username, pwd, display, role_code in USERS:
            u = User(
                username=username, display_name=display,
                password_hash=PasswordHasher.hash(pwd),
                is_superuser=(role_code is None),
            )
            if role_code:
                u.roles = [role_map[role_code]]
            db.add(u)

        # 4. 组织
        dept_map = {}
        for code, name, leader, phone in DEPARTMENTS:
            d = Department(code=code, name=name, leader=leader, phone=phone)
            db.add(d)
            dept_map[code] = d
        db.flush()
        for emp_no, name, gender, phone, email, hire, pos, dept_code in EMPLOYEES:
            db.add(Employee(
                emp_no=emp_no, name=name, gender=gender, phone=phone, email=email,
                hire_date=date.fromisoformat(hire), position=pos,
                department_id=dept_map[dept_code].id,
            ))

        # 5. 基础资料
        cat_map = {}
        for name in CATEGORIES:
            c = ProductCategory(name=name)
            db.add(c)
            cat_map[name] = c
        db.flush()
        product_map = {}
        for code, name, spec, unit, cat, buy, sell, safety in PRODUCTS:
            p = Product(
                code=code, name=name, spec=spec, unit=unit,
                category_id=cat_map[cat].id, purchase_price=Decimal(str(buy)),
                sale_price=Decimal(str(sell)), safety_stock=Decimal(str(safety)),
            )
            db.add(p)
            product_map[code] = p
        for code, name, contact, phone, addr, credit in CUSTOMERS:
            db.add(Customer(code=code, name=name, contact=contact, phone=phone,
                            address=addr, credit_limit=Decimal(str(credit))))
        for code, name, contact, phone, addr in SUPPLIERS:
            db.add(Supplier(code=code, name=name, contact=contact, phone=phone, address=addr))
        wh_map = {}
        for code, name, addr, mgr in WAREHOUSES:
            w = Warehouse(code=code, name=name, address=addr, manager=mgr)
            db.add(w)
            wh_map[code] = w
        db.flush()

        # 6. 期初库存（走统一库存服务，保证流水完整）
        for pcode, wcode, qty in INITIAL_STOCKS:
            change_stock(
                db, product_id=product_map[pcode].id, warehouse_id=wh_map[wcode].id,
                delta=Decimal(qty), log_type="initial", ref_no="SEED",
                created_by="system", remark="期初建账",
            )

        db.commit()
        print("[seed] 初始化完成：权限/角色/账号/基础数据/期初库存")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()