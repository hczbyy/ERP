# OpenERP 接口自动化测试

基于接口文档 `api.md` 生成的 PO 模式接口自动化测试工程（Python + pytest + requests + Allure）。

## 项目结构

```
├── api.md                # 接口文档（来源）
├── conftest.py           # token 管理、API 实例、依赖数据 fixture（自动创建/清理）
├── pytest.ini            # pytest 配置（用例目录、Allure 输出）
├── requirements.txt      # 依赖清单
├── common/               # 公共层：配置、日志、请求客户端、断言、数据工厂
│   ├── config.py         #   环境/账号/超时（支持环境变量覆盖）
│   ├── client.py         #   HTTP 客户端：Bearer token、401 自动重登
│   ├── assertions.py     #   统一断言：code==0 / 业务失败 / 401 / 404 / 422
│   ├── data.py           #   唯一编码/随机数据生成
│   └── logger.py         #   控制台 + 滚动文件日志
├── api/                  # API 层（PO 对象）：接口方法即页面操作
│   ├── base.py
│   ├── auth_api.py       #   认证
│   ├── dashboard_api.py  #   仪表盘 + 健康检查
│   ├── master_api.py     #   基础数据（分类/商品/客户/供应商/仓库）
│   ├── inventory_api.py  #   库存（查询/流水/盘点/调拨）
│   ├── system_api.py     #   系统（用户/角色/权限/部门/员工/审计）
│   ├── finance_api.py    #   财务（应收/应付/收款/付款）
│   ├── purchase_api.py   #   采购（订单/入库单）
│   └── sales_api.py      #   销售（订单/出库单）
└── testcases/            # 测试用例层（正向/边界/异常 + Allure 注解）
    ├── test_auth.py
    ├── test_dashboard.py
    ├── test_master.py
    ├── test_inventory.py
    ├── test_system.py
    ├── test_finance.py
    ├── test_purchase.py
    └── test_sales.py
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动被测服务（OpenERP，默认 http://127.0.0.1:8000）

# 3. 运行全部用例
pytest

# 4. 生成 Allure 报告
allure generate allure-results -o allure-report --clean
allure open allure-report
```

## 配置

通过环境变量切换环境与账号（默认即为文档约定值）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ERP_BASE_URL` | `http://127.0.0.1:8000` | 服务地址 |
| `ERP_USERNAME` | `admin` | 登录账号 |
| `ERP_PASSWORD` | `admin123` | 登录密码 |
| `ERP_TIMEOUT` | `15` | 请求超时（秒） |

示例：`$env:ERP_BASE_URL="http://10.0.0.8:8000"; pytest`

## 设计说明

- **PO 分层**：`api/` 为页面对象层（接口操作），`testcases/` 只做场景编排与断言；
- **Token 管理**：`conftest.py` 的 session 级 `client` fixture 启动即登录，token 失效（401）自动重登重试；
- **依赖数据自洽**：分类/商品/客户/供应商/仓库/部门等基础数据由 fixture 动态创建、用例结束自动删除，用例可重复执行、互不污染；
- **状态流转用例**：采购/销售订单覆盖 创建→审核→收货/发货 完整链路，以及取消后再次审核/收货/发货等状态不允许异常；
- **不确定结构**：订单明细 `items`、盘点结果 `items` 的元素结构文档未给出，按常见约定实现（见 `conftest.py::order_items` 与 `test_inventory.py` 注释），如与实际接口不符请按实际调整。