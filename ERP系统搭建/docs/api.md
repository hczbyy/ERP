# OpenERP 企业资源管理系统 API 接口文档

> 版本：1.0.0 ｜ Base URL：`http://127.0.0.1:8000`
> OpenERP 企业资源管理系统：采购、销售、库存、财务一体化

## 通用约定

### 认证方式

登录成功后获取 `token`，除登录/健康检查外所有接口需在请求头携带：

```http
Authorization: Bearer <token>
```

### 统一响应格式

```json
{"code": 0, "message": "success", "data": {...}}
```

| 字段 | 说明 |
| --- | --- |
| code | 0 成功；非 0 业务失败（通常 1） |
| message | 提示信息（业务错误时可直接展示给用户） |
| data | 业务数据，结构见各接口 |

### 错误状态码

| HTTP 状态码 | 含义 |
| --- | --- |
| 400 | 业务规则冲突（库存不足、状态不允许等），响应体为 `{code:1, message, data:null}` |
| 401 | 未登录 / 凭证无效或过期 |
| 403 | 无权限（缺少对应权限点） |
| 500 | 服务器内部错误 |

### 分页参数

列表接口通用查询参数：`page`（页码，默认 1）、`page_size`（每页数量，默认 20）、`keyword`（搜索关键字）。

---

## 接口总览

| 模块 | 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- | --- |
| 仪表盘 | GET | `/api/dashboard/summary` | Summary | 公开 |
| 仪表盘 | GET | `/api/dashboard/sales-trend` | Sales Trend | 公开 |
| 仪表盘 | GET | `/api/dashboard/top-products` | Top Products | 公开 |
| 仪表盘 | GET | `/api/dashboard/low-stocks` | Low Stocks | 公开 |
| 仪表盘 | GET | `/api/dashboard/recent-orders` | Recent Orders | 公开 |
| 其他 | GET | `/api/health` | Health | 公开 |
| 基础数据 | GET | `/api/master/categories` | List Categories | 公开 |
| 基础数据 | POST | `/api/master/categories` | Create Category | 公开 |
| 基础数据 | PUT | `/api/master/categories/{cat_id}` | Update Category | 公开 |
| 基础数据 | DELETE | `/api/master/categories/{cat_id}` | Delete Category | 公开 |
| 基础数据 | GET | `/api/master/products` | List Products | 公开 |
| 基础数据 | POST | `/api/master/products` | Create Product | 公开 |
| 基础数据 | GET | `/api/master/products/all` | All Products | 公开 |
| 基础数据 | PUT | `/api/master/products/{product_id}` | Update Product | 公开 |
| 基础数据 | DELETE | `/api/master/products/{product_id}` | Delete Product | 公开 |
| 基础数据 | GET | `/api/master/customers` | List Customers | 公开 |
| 基础数据 | POST | `/api/master/customers` | Create Customer | 公开 |
| 基础数据 | GET | `/api/master/customers/all` | All Customers | 公开 |
| 基础数据 | PUT | `/api/master/customers/{cust_id}` | Update Customer | 公开 |
| 基础数据 | DELETE | `/api/master/customers/{cust_id}` | Delete Customer | 公开 |
| 基础数据 | GET | `/api/master/suppliers` | List Suppliers | 公开 |
| 基础数据 | POST | `/api/master/suppliers` | Create Supplier | 公开 |
| 基础数据 | GET | `/api/master/suppliers/all` | All Suppliers | 公开 |
| 基础数据 | PUT | `/api/master/suppliers/{sup_id}` | Update Supplier | 公开 |
| 基础数据 | DELETE | `/api/master/suppliers/{sup_id}` | Delete Supplier | 公开 |
| 基础数据 | GET | `/api/master/warehouses` | List Warehouses | 公开 |
| 基础数据 | POST | `/api/master/warehouses` | Create Warehouse | 公开 |
| 基础数据 | PUT | `/api/master/warehouses/{wh_id}` | Update Warehouse | 公开 |
| 基础数据 | DELETE | `/api/master/warehouses/{wh_id}` | Delete Warehouse | 公开 |
| 库存管理 | GET | `/api/inventory/stocks` | List Stocks | 公开 |
| 库存管理 | GET | `/api/inventory/logs` | List Logs | 公开 |
| 库存管理 | GET | `/api/inventory/checks` | List Checks | 公开 |
| 库存管理 | POST | `/api/inventory/checks` | Create Check | 公开 |
| 库存管理 | GET | `/api/inventory/checks/{check_id}` | Check Detail | 公开 |
| 库存管理 | PUT | `/api/inventory/checks/{check_id}` | Update Check | 公开 |
| 库存管理 | POST | `/api/inventory/checks/{check_id}/done` | Done Check | 公开 |
| 库存管理 | GET | `/api/inventory/transfers` | List Transfers | 公开 |
| 库存管理 | POST | `/api/inventory/transfers` | Create Transfer | 公开 |
| 系统管理 | GET | `/api/system/users` | List Users | 公开 |
| 系统管理 | POST | `/api/system/users` | Create User | 公开 |
| 系统管理 | PUT | `/api/system/users/{user_id}` | Update User | 公开 |
| 系统管理 | DELETE | `/api/system/users/{user_id}` | Delete User | 公开 |
| 系统管理 | POST | `/api/system/users/{user_id}/toggle-active` | Toggle User | 公开 |
| 系统管理 | GET | `/api/system/roles` | List Roles | 公开 |
| 系统管理 | POST | `/api/system/roles` | Create Role | 公开 |
| 系统管理 | GET | `/api/system/permissions` | List Permissions | 公开 |
| 系统管理 | PUT | `/api/system/roles/{role_id}` | Update Role | 公开 |
| 系统管理 | DELETE | `/api/system/roles/{role_id}` | Delete Role | 公开 |
| 系统管理 | GET | `/api/system/departments` | List Departments | 公开 |
| 系统管理 | POST | `/api/system/departments` | Create Department | 公开 |
| 系统管理 | PUT | `/api/system/departments/{dept_id}` | Update Department | 公开 |
| 系统管理 | DELETE | `/api/system/departments/{dept_id}` | Delete Department | 公开 |
| 系统管理 | GET | `/api/system/employees` | List Employees | 公开 |
| 系统管理 | POST | `/api/system/employees` | Create Employee | 公开 |
| 系统管理 | PUT | `/api/system/employees/{emp_id}` | Update Employee | 公开 |
| 系统管理 | DELETE | `/api/system/employees/{emp_id}` | Delete Employee | 公开 |
| 系统管理 | GET | `/api/system/audit-logs` | List Audit Logs | 公开 |
| 认证 | POST | `/api/auth/login` | Login | 公开 |
| 认证 | GET | `/api/auth/me` | Me | 公开 |
| 认证 | GET | `/api/auth/permissions` | Permissions | 公开 |
| 认证 | POST | `/api/auth/change-password` | Change Password | 公开 |
| 财务管理 | GET | `/api/finance/receivables` | List Receivables | 公开 |
| 财务管理 | GET | `/api/finance/payables` | List Payables | 公开 |
| 财务管理 | GET | `/api/finance/receipts` | List Receipts | 公开 |
| 财务管理 | POST | `/api/finance/receipts` | Create Receipt | 公开 |
| 财务管理 | GET | `/api/finance/payments` | List Payments | 公开 |
| 财务管理 | POST | `/api/finance/payments` | Create Payment | 公开 |
| 采购管理 | GET | `/api/purchase/orders` | List Orders | 公开 |
| 采购管理 | POST | `/api/purchase/orders` | Create Order | 公开 |
| 采购管理 | GET | `/api/purchase/orders/{order_id}` | Order Detail | 公开 |
| 采购管理 | PUT | `/api/purchase/orders/{order_id}` | Update Order | 公开 |
| 采购管理 | DELETE | `/api/purchase/orders/{order_id}` | Delete Order | 公开 |
| 采购管理 | POST | `/api/purchase/orders/{order_id}/approve` | Approve Order | 公开 |
| 采购管理 | POST | `/api/purchase/orders/{order_id}/cancel` | Cancel Order | 公开 |
| 采购管理 | POST | `/api/purchase/orders/{order_id}/receive` | Receive Order | 公开 |
| 采购管理 | GET | `/api/purchase/stock-ins` | List Stock Ins | 公开 |
| 采购管理 | GET | `/api/purchase/stock-ins/{si_id}` | Stock In Detail | 公开 |
| 销售管理 | GET | `/api/sales/orders` | List Orders | 公开 |
| 销售管理 | POST | `/api/sales/orders` | Create Order | 公开 |
| 销售管理 | GET | `/api/sales/orders/{order_id}` | Order Detail | 公开 |
| 销售管理 | PUT | `/api/sales/orders/{order_id}` | Update Order | 公开 |
| 销售管理 | DELETE | `/api/sales/orders/{order_id}` | Delete Order | 公开 |
| 销售管理 | POST | `/api/sales/orders/{order_id}/approve` | Approve Order | 公开 |
| 销售管理 | POST | `/api/sales/orders/{order_id}/cancel` | Cancel Order | 公开 |
| 销售管理 | POST | `/api/sales/orders/{order_id}/ship` | Ship Order | 公开 |
| 销售管理 | GET | `/api/sales/stock-outs` | List Stock Outs | 公开 |
| 销售管理 | GET | `/api/sales/stock-outs/{so_id}` | Stock Out Detail | 公开 |

---

## 仪表盘

### GET `/api/dashboard/summary`

**Summary**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### GET `/api/dashboard/sales-trend`

**Sales Trend**

近 N 天每日销售金额与订单数。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| days | query | integer | 否 | - |

### GET `/api/dashboard/top-products`

**Top Products**

销量 TOP N 商品（按出库明细聚合）。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| limit | query | integer | 否 | - |

### GET `/api/dashboard/low-stocks`

**Low Stocks**

库存预警列表。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| limit | query | integer | 否 | - |

### GET `/api/dashboard/recent-orders`

**Recent Orders**

最近销售订单（首页列表）。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| limit | query | integer | 否 | - |

---

## 其他

### GET `/api/health`

**Health**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

---

## 基础数据

### GET `/api/master/categories`

**List Categories**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### POST `/api/master/categories`

**Create Category**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`CategoryBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | - || sort | integer | 否 | - |

### PUT `/api/master/categories/{cat_id}`

**Update Category**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| cat_id | path | integer | 是 | - |

**请求体（`CategoryBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| name | string | 是 | - || sort | integer | 否 | - |

### DELETE `/api/master/categories/{cat_id}`

**Delete Category**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| cat_id | path | integer | 是 | - |

### GET `/api/master/products`

**List Products**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || category_id | query | - | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/master/products`

**Create Product**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`ProductBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || spec | object | 否 | - || unit | string | 否 | - || barcode | object | 否 | - || category_id | object | 否 | - || purchase_price | number | 否 | - || sale_price | number | 否 | - || safety_stock | number | 否 | - || status | string | 否 | - || description | object | 否 | - |

### GET `/api/master/products/all`

**All Products**

下拉选择用：返回全量（含当前库存，前端做库存校验提示）。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - |

### PUT `/api/master/products/{product_id}`

**Update Product**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| product_id | path | integer | 是 | - |

**请求体（`ProductBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || spec | object | 否 | - || unit | string | 否 | - || barcode | object | 否 | - || category_id | object | 否 | - || purchase_price | number | 否 | - || sale_price | number | 否 | - || safety_stock | number | 否 | - || status | string | 否 | - || description | object | 否 | - |

### DELETE `/api/master/products/{product_id}`

**Delete Product**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| product_id | path | integer | 是 | - |

### GET `/api/master/customers`

**List Customers**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/master/customers`

**Create Customer**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`CustomerBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || contact | object | 否 | - || phone | object | 否 | - || address | object | 否 | - || credit_limit | number | 否 | - || status | string | 否 | - |

### GET `/api/master/customers/all`

**All Customers**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - |

### PUT `/api/master/customers/{cust_id}`

**Update Customer**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| cust_id | path | integer | 是 | - |

**请求体（`CustomerBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || contact | object | 否 | - || phone | object | 否 | - || address | object | 否 | - || credit_limit | number | 否 | - || status | string | 否 | - |

### DELETE `/api/master/customers/{cust_id}`

**Delete Customer**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| cust_id | path | integer | 是 | - |

### GET `/api/master/suppliers`

**List Suppliers**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/master/suppliers`

**Create Supplier**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`SupplierBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || contact | object | 否 | - || phone | object | 否 | - || address | object | 否 | - || status | string | 否 | - |

### GET `/api/master/suppliers/all`

**All Suppliers**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - |

### PUT `/api/master/suppliers/{sup_id}`

**Update Supplier**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| sup_id | path | integer | 是 | - |

**请求体（`SupplierBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || contact | object | 否 | - || phone | object | 否 | - || address | object | 否 | - || status | string | 否 | - |

### DELETE `/api/master/suppliers/{sup_id}`

**Delete Supplier**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| sup_id | path | integer | 是 | - |

### GET `/api/master/warehouses`

**List Warehouses**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### POST `/api/master/warehouses`

**Create Warehouse**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`WarehouseBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || address | object | 否 | - || manager | object | 否 | - || status | string | 否 | - |

### PUT `/api/master/warehouses/{wh_id}`

**Update Warehouse**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| wh_id | path | integer | 是 | - |

**请求体（`WarehouseBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || address | object | 否 | - || manager | object | 否 | - || status | string | 否 | - |

### DELETE `/api/master/warehouses/{wh_id}`

**Delete Warehouse**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| wh_id | path | integer | 是 | - |

---

## 库存管理

### GET `/api/inventory/stocks`

**List Stocks**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || warehouse_id | query | - | 否 | - || low_stock_only | query | boolean | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### GET `/api/inventory/logs`

**List Logs**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| product_id | query | - | 否 | - || warehouse_id | query | - | 否 | - || log_type | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### GET `/api/inventory/checks`

**List Checks**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/inventory/checks`

**Create Check**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`CheckCreateBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| warehouse_id | integer | 是 | - || remark | object | 否 | - || product_ids | array | 是 | - |

### GET `/api/inventory/checks/{check_id}`

**Check Detail**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| check_id | path | integer | 是 | - |

### PUT `/api/inventory/checks/{check_id}`

**Update Check**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| check_id | path | integer | 是 | - |

**请求体（`CheckUpdateBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| items | array | 是 | - |

### POST `/api/inventory/checks/{check_id}/done`

**Done Check**

提交盘点：按差异调整库存（盘盈入、盘亏出），生成调整流水。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| check_id | path | integer | 是 | - |

### GET `/api/inventory/transfers`

**List Transfers**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/inventory/transfers`

**Create Transfer**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`TransferBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| from_warehouse_id | integer | 是 | - || to_warehouse_id | integer | 是 | - || remark | object | 否 | - || items | array | 是 | - |

---

## 系统管理

### GET `/api/system/users`

**List Users**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/system/users`

**Create User**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`UserBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | - || display_name | string | 是 | - || password | object | 否 | - || email | object | 否 | - || phone | object | 否 | - || role_ids | array | 否 | - |

### PUT `/api/system/users/{user_id}`

**Update User**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| user_id | path | integer | 是 | - |

**请求体（`UserBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | - || display_name | string | 是 | - || password | object | 否 | - || email | object | 否 | - || phone | object | 否 | - || role_ids | array | 否 | - |

### DELETE `/api/system/users/{user_id}`

**Delete User**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| user_id | path | integer | 是 | - |

### POST `/api/system/users/{user_id}/toggle-active`

**Toggle User**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| user_id | path | integer | 是 | - |

### GET `/api/system/roles`

**List Roles**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### POST `/api/system/roles`

**Create Role**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`RoleBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || description | object | 否 | - || permission_ids | array | 否 | - |

### GET `/api/system/permissions`

**List Permissions**

全部权限点（分组返回，前端配置角色用）。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### PUT `/api/system/roles/{role_id}`

**Update Role**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| role_id | path | integer | 是 | - |

**请求体（`RoleBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || description | object | 否 | - || permission_ids | array | 否 | - |

### DELETE `/api/system/roles/{role_id}`

**Delete Role**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| role_id | path | integer | 是 | - |

### GET `/api/system/departments`

**List Departments**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### POST `/api/system/departments`

**Create Department**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`DeptBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || leader | object | 否 | - || phone | object | 否 | - || remark | object | 否 | - |

### PUT `/api/system/departments/{dept_id}`

**Update Department**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| dept_id | path | integer | 是 | - |

**请求体（`DeptBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| code | string | 是 | - || name | string | 是 | - || leader | object | 否 | - || phone | object | 否 | - || remark | object | 否 | - |

### DELETE `/api/system/departments/{dept_id}`

**Delete Department**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| dept_id | path | integer | 是 | - |

### GET `/api/system/employees`

**List Employees**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/system/employees`

**Create Employee**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`EmployeeBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| emp_no | string | 是 | - || name | string | 是 | - || gender | object | 否 | - || phone | object | 否 | - || email | object | 否 | - || hire_date | object | 否 | - || position | object | 否 | - || status | string | 否 | - || department_id | object | 否 | - |

### PUT `/api/system/employees/{emp_id}`

**Update Employee**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| emp_id | path | integer | 是 | - |

**请求体（`EmployeeBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| emp_no | string | 是 | - || name | string | 是 | - || gender | object | 否 | - || phone | object | 否 | - || email | object | 否 | - || hire_date | object | 否 | - || position | object | 否 | - || status | string | 否 | - || department_id | object | 否 | - |

### DELETE `/api/system/employees/{emp_id}`

**Delete Employee**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| emp_id | path | integer | 是 | - |

### GET `/api/system/audit-logs`

**List Audit Logs**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || action | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

---

## 认证

### POST `/api/auth/login`

**Login**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`LoginBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| username | string | 是 | - || password | string | 是 | - |

### GET `/api/auth/me`

**Me**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### GET `/api/auth/permissions`

**Permissions**

当前用户拥有的权限点（前端据此渲染菜单/按钮）。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

### POST `/api/auth/change-password`

**Change Password**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`ChangePwdBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| old_password | string | 是 | - || new_password | string | 是 | - |

---

## 财务管理

### GET `/api/finance/receivables`

**List Receivables**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - || keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### GET `/api/finance/payables`

**List Payables**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - || keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### GET `/api/finance/receipts`

**List Receipts**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/finance/receipts`

**Create Receipt**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`ReceiptBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| receivable_id | integer | 是 | - || amount | number | 是 | - || pay_method | string | 否 | - || received_at | object | 否 | - || remark | object | 否 | - |

### GET `/api/finance/payments`

**List Payments**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/finance/payments`

**Create Payment**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`PaymentBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| payable_id | integer | 是 | - || amount | number | 是 | - || pay_method | string | 否 | - || paid_at | object | 否 | - || remark | object | 否 | - |

---

## 采购管理

### GET `/api/purchase/orders`

**List Orders**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - || keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/purchase/orders`

**Create Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`app__api__purchase__OrderBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| supplier_id | integer | 是 | - || warehouse_id | integer | 是 | - || remark | object | 否 | - || items | array | 是 | - |

### GET `/api/purchase/orders/{order_id}`

**Order Detail**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

### PUT `/api/purchase/orders/{order_id}`

**Update Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

**请求体（`app__api__purchase__OrderBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| supplier_id | integer | 是 | - || warehouse_id | integer | 是 | - || remark | object | 否 | - || items | array | 是 | - |

### DELETE `/api/purchase/orders/{order_id}`

**Delete Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

### POST `/api/purchase/orders/{order_id}/approve`

**Approve Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

### POST `/api/purchase/orders/{order_id}/cancel`

**Cancel Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

**请求体（`CancelBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| reason | object | 否 | - |

### POST `/api/purchase/orders/{order_id}/receive`

**Receive Order**

收货入库：生成入库单 + 库存增加 + 应付挂账。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

**请求体（`ReceiveBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| remark | object | 否 | - || items | array | 是 | - |

### GET `/api/purchase/stock-ins`

**List Stock Ins**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### GET `/api/purchase/stock-ins/{si_id}`

**Stock In Detail**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| si_id | path | integer | 是 | - |

---

## 销售管理

### GET `/api/sales/orders`

**List Orders**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| status | query | string | 否 | - || keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### POST `/api/sales/orders`

**Create Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求体（`app__api__sales__OrderBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| customer_id | integer | 是 | - || warehouse_id | integer | 是 | - || remark | object | 否 | - || items | array | 是 | - |

### GET `/api/sales/orders/{order_id}`

**Order Detail**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

### PUT `/api/sales/orders/{order_id}`

**Update Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

**请求体（`app__api__sales__OrderBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| customer_id | integer | 是 | - || warehouse_id | integer | 是 | - || remark | object | 否 | - || items | array | 是 | - |

### DELETE `/api/sales/orders/{order_id}`

**Delete Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

### POST `/api/sales/orders/{order_id}/approve`

**Approve Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

### POST `/api/sales/orders/{order_id}/cancel`

**Cancel Order**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

**请求体（`CancelBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| reason | object | 否 | - |

### POST `/api/sales/orders/{order_id}/ship`

**Ship Order**

发货出库：生成出库单 + 库存扣减 + 应收挂账。

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| order_id | path | integer | 是 | - |

**请求体（`ShipBody`）**

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| remark | object | 否 | - || items | array | 是 | - |

### GET `/api/sales/stock-outs`

**List Stock Outs**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| keyword | query | string | 否 | - || page | query | integer | 否 | - || page_size | query | integer | 否 | - |

### GET `/api/sales/stock-outs/{so_id}`

**Stock Out Detail**

- 权限：公开
- 响应 `data` 结构：动态结构（运行时确定）

**请求参数**

| 名称 | 位置 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- | --- |
| so_id | path | integer | 是 | - |

---
