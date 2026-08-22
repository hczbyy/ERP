# ERP 系统搭建与自动化测试

本仓库包含 ERP 系统的两个实现版本（FastAPI 版、Spring Boot 版），以及配套的接口自动化测试工程、JMeter 接口测试脚本和一个 AI 接口测试平台。

## 仓库结构

```text
ERP-test/
├── fastapi版ERP/      # OpenERP 企业资源管理系统（FastAPI + SQLAlchemy + 原生前端）
├── springboot版ERP/   # OpenERP 企业资源管理系统（Spring Boot 3 + JDK 21 + MySQL + Redis）
├── ERP+jmeter/        # JMeter 接口测试脚本（登录、基础数据）
├── 自动化测试/         # pytest + requests + Allure 接口自动化测试工程
├── ai测试平台/         # AI 接口测试平台（导入文档 → AI 生成用例 → 执行 → HTML 报告）
└── README.md          # 本文件
```

---

## fastapi版ERP

用于软件测试的 ERP 系统，包含采购、销售、库存、财务、系统管理等一体化功能模块，前端为原生页面，后端提供完整 REST API。

- 技术栈：Python 3.10+ / FastAPI / SQLAlchemy / SQLite / PyJWT / Pydantic
- 启动：

```bash
cd fastapi版ERP/backend
pip install -r requirements.txt
python run.py
```

Windows 下也可直接双击 `backend/start.bat`。启动后访问 <http://127.0.0.1:8000>，首次启动自动写入演示数据，在线接口文档见 `/docs`。

更详细的说明见 `fastapi版ERP/README.md`。

---

## springboot版ERP

使用 **Spring Boot 3.3.5 + JDK 21 + MySQL 8 + Redis** 完整重写的 ERP，功能与 FastAPI 版一致，REST 接口兼容。

- 技术栈：Java 21 / Spring Boot 3.3.5 / Spring Data JPA / MySQL / Redis / JWT
- 环境依赖：MySQL 8（数据库 `openerp`，应用账号 `erp/123456`）、Redis（127.0.0.1:6379）
- 启动方式：
  - IDEA：用 JDK 21 打开项目，运行主类 `com.openerp.OpenErpApplication`；
  - 命令行：双击 `start.bat`（会自动拉起 Redis），或 `mvn spring-boot:run`。
- 访问 <http://127.0.0.1:8080>，首次启动自动建表并写入演示数据（幂等）。

更详细的说明见 `springboot版ERP/README.md`。

---

## 自动化测试

基于接口文档生成的 PO 模式接口自动化测试工程（Python + pytest + requests + Allure），覆盖认证、仪表盘、基础数据、采购、销售、库存、财务、系统管理全部模块的正向、边界与异常用例。

```bash
cd 自动化测试
pip install -r requirements.txt
pytest
```

启动被测 ERP 服务（FastAPI 版默认 `http://127.0.0.1:8000`）后即可执行。更详细的说明见 `自动化测试/README.md`。

---

## ERP+jmeter

基于 Apache JMeter 5.6.3 的接口测试工程，覆盖 ERP 系统的登录与基础数据模块，打开对应 `.jmx` 文件即可运行（测试前需先启动被测 ERP 服务）。

---

## ai测试平台

本地接口测试平台：**导入接口文档 → AI 生成测试用例 → 人工编辑维护 → 执行用例 → 自动生成 HTML 测试报告**，全程无需编写代码。

- 支持 OpenAPI 3.x / Swagger 2.0 / Postman Collection v2.1 / Markdown 接口文档导入；
- AI 生成用例可接入任意 OpenAI 兼容大模型（DeepSeek / 通义千问 / OpenAI / 本地 Ollama 等），未配置 API Key 时使用内置规则模式离线生成；
- 数据保存在本机 SQLite，报告保存在 `reports` 目录，无需联网、数据不外传。

```bash
cd ai测试平台
python start.py
```

Windows 下双击 `启动平台.bat` 即可，浏览器访问 <http://127.0.0.1:8000>。更详细的说明见 `ai测试平台/README.md`。

---

## 演示账号（两个 ERP 版本通用）

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 超级管理员 |
| purchaser | demo123 | 采购经理 |
| sales | demo123 | 销售经理 |
| keeper | demo123 | 仓管员 |
| finance | demo123 | 财务专员 |
| auditor | demo123 | 审计员 |
