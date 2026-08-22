# OpenERP 企业资源管理系统（Spring Boot 版）

原 E:\ERP\ERP系统搭建 中的 FastAPI 版 ERP 已用 **Spring Boot 3 + JDK 21 + MySQL + Redis** 完整重写，项目位于 `D:\springboot`，运行依赖位于 `D:\springboot依赖`。

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 登录认证 | JWT 登录、修改密码、角色权限控制（Token 会话存于 Redis） |
| 仪表盘 | 经营数据总览、销售趋势、TOP 商品、库存预警、最近订单 |
| 基础资料 | 商品分类、商品、客户、供应商、仓库 |
| 采购管理 | 采购单、审核、取消、收货入库 |
| 销售管理 | 销售单、审核、取消、发货出库 |
| 库存管理 | 库存查询、流水、盘点、调拨 |
| 财务管理 | 应收应付、收款付款核销 |
| 系统管理 | 用户、角色权限、部门、员工、审计日志 |

## 环境说明（全部在 D 盘）

- JDK 21：`D:\jdk21`
- Maven：`D:\springboot依赖\maven\apache-maven-3.9.9`（本地仓库 `D:\springboot依赖\maven-repo`）
- Redis：`D:\springboot依赖\redis`
- MySQL：本机 MySQL 8 服务（root/123456），数据库 `openerp`，应用账号 `erp/123456`

## 启动步骤

1. 确保 MySQL 服务已启动（本机服务 MySQL80）。
2. 双击 `start-redis.bat` 启动 Redis（或先运行一次 `start.bat`，会自动拉起 Redis）。
3. 双击 `start.bat` 编译并启动系统。
4. 浏览器访问 <http://127.0.0.1:8080>。

首次启动会自动创建数据库表并写入演示数据（幂等，已有数据则跳过）。

## 演示账号

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 超级管理员 |
| purchaser | demo123 | 采购经理 |
| sales | demo123 | 销售经理 |
| keeper | demo123 | 仓管员 |
| finance | demo123 | 财务专员 |
| auditor | demo123 | 审计员 |

## 技术要点

- 统一响应格式 `{code, message, data}`，与原系统接口完全兼容。
- JWT 令牌同时写入 Redis（key：`erp:token:{userId}`，8 小时过期），实现服务端会话管理。
- Redis 还用于商品下拉列表缓存（60 秒）。
- 库存变动统一走库存服务，每次变动伴随一条流水，保证可追溯；采购收货/销售发货/盘点/调拨均为事务操作。

## 目录结构

```text
D:\springboot
├── pom.xml
├── start.bat / start-redis.bat
├── README.md
└── src\main
    ├── java\com\openerp
    │   ├── controller   # REST 接口
    │   ├── service      # 业务逻辑
    │   ├── repository   # 数据访问
    │   ├── entity       # 数据模型
    │   ├── config       # 鉴权/Redis/Jackson 配置
    │   └── seed         # 演示数据初始化
    └── resources
        ├── application.yml
        └── static       # 前端页面（原 ERP 前端）
```
