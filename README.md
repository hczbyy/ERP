# ERP 系统搭建与接口自动化测试

本仓库包含两个部分：一个用于软件测试的 ERP 系统（OpenERP 企业资源管理系统），以及一套针对该系统接口的 pytest 自动化测试工程。

## 仓库结构

```text
ERP/
├── ERP系统搭建/     # OpenERP 企业资源管理系统（FastAPI + SQLAlchemy + 原生前端）
├── 自动化测试/      # pytest + requests + Allure 接口自动化测试工程
└── README.md        # 本文件
```

---

## ERP系统搭建

用于软件测试的 ERP 系统，包含采购、销售、库存、财务、系统管理等一体化功能模块，前端为原生页面，后端提供完整 REST API。

## 技术栈

- 后端：Python 3.10+ / FastAPI / SQLAlchemy / SQLite / PyJWT / Pydantic
- 前端：原生 HTML / CSS / JavaScript
- 测试：pytest

## 功能模块

| 模块 | 说明 |
| --- | --- |
| 登录认证 | JWT 登录、修改密码、角色权限控制 |
| 仪表盘 | 经营数据总览 |
| 基础资料 | 商品、客户、供应商、仓库管理 |
| 采购管理 | 采购单、审核、收货 |
| 销售管理 | 销售单、审核、发货 |
| 库存管理 | 库存查询、盘点、调拨 |
| 财务管理 | 财务查询、收付款核销 |
| 系统管理 | 用户、角色、组织架构、审计日志 |

## 演示账号

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 超级管理员 |
| purchaser | demo123 | 采购经理 |
| sales | demo123 | 销售经理 |
| keeper | demo123 | 仓管员 |
| finance | demo123 | 财务专员 |
| auditor | demo123 | 审计员 |

## 快速启动

```bash
cd backend
pip install -r requirements.txt
python run.py
```

也可以直接运行 `python app/main.py`，或使用 `uvicorn app.main:app`；Windows 下双击 `backend/start.bat` 可一键启动。启动后浏览器访问 <http://127.0.0.1:8000>。

首次启动会自动写入演示数据（SQLite 数据库 `backend/data/erp.db`）。

## 运行测试

```bash
cd backend
pytest
```

## 目录结构

```text
ERP系统搭建/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── api/             # 接口路由（auth、purchase、sales、inventory、finance 等）
│   │   ├── models/          # 数据模型
│   │   ├── services/        # 业务逻辑
│   │   ├── utils/           # 通用工具（分页、安全）
│   │   ├── database.py      # 数据库连接
│   │   ├── seed.py          # 演示数据初始化
│   │   └── main.py          # 应用入口
│   ├── data/                # SQLite 数据库文件
│   ├── tests/               # 自动化测试
│   ├── requirements.txt
│   ├── run.py
│   └── start.bat
├── frontend/                # 前端页面（HTML / CSS / JS）
├── docs/                    # 接口文档（api.md、openapi.json）
└── browser_verification/    # Selenium + Edge 浏览器全量验证脚本
```

## 接口文档

启动服务后，可访问 FastAPI 自带的 `/docs` 查看在线接口文档；`docs/api.md` 和 `docs/openapi.json` 中也有完整的接口说明。

---

## 自动化测试

基于接口文档 `自动化测试/api.md` 生成的 PO 模式接口自动化测试工程（Python + pytest + requests + Allure），覆盖认证、仪表盘、基础数据、采购、销售、库存、财务、系统管理全部模块的正向、边界与异常用例。

### 快速开始

```bash
cd 自动化测试
pip install -r requirements.txt
pytest
```

启动被测服务（默认 `http://127.0.0.1:8000`）后可执行全部用例；测试结果通过 Allure 生成报告：

```bash
allure generate allure-results -o allure-report --clean
allure open allure-report
```

### 配置

通过环境变量切换环境与账号（默认即为文档约定值）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ERP_BASE_URL` | `http://127.0.0.1:8000` | 被测服务地址 |
| `ERP_USERNAME` | `admin` | 登录账号 |
| `ERP_PASSWORD` | `admin123` | 登录密码 |
| `ERP_TIMEOUT` | `15` | 请求超时（秒） |

### 分层设计

- `api/`：API 层（PO 对象），一个模块一个接口类；
- `common/`：公共层（配置、请求客户端、断言、数据工厂、日志）；
- `testcases/`：测试用例层（正向、边界、异常 + Allure 注解）；
- `conftest.py`：Token 管理、API 实例与依赖数据 fixture。

更详细的说明见 `自动化测试/README.md`。
