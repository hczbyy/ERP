# AI 接口测试平台

一个可以直接在软件测试工作中使用的本地接口测试平台：**导入接口文档 → AI 生成测试用例 → 人工编辑维护 → 执行用例 → 自动生成 HTML 测试报告**，全程无需编写代码。

## 功能清单

- **接口文档导入**：支持 OpenAPI 3.x / Swagger 2.0（JSON、YAML）、Postman Collection v2.1 和 Markdown 接口文档（`### GET /path` + 参数/请求体表格），也支持直接粘贴文档内容
- **AI 生成测试用例**：接入任意 OpenAI 兼容的大模型（DeepSeek / 通义千问 / OpenAI / 本地 Ollama 等），按“正常路径 / 参数校验 / 业务场景 / 全面覆盖”分层生成，断言到字段级
- **规则模式**：未配置 API Key 时，基于接口 Schema 自动生成等价类、边界值、非法枚举等用例，离线可用
- **用例管理**：可视化编辑请求头、查询参数、路径参数、请求体、字段级断言，支持新增、复制、启停用、批量删除
- **执行引擎**：支持环境切换、`{{变量}}` 渲染、Token 占位、多断言校验、超时控制
- **自动测试报告**：执行完成后自动生成独立 HTML 报告（通过率、通过/失败/错误统计、请求/响应/断言明细），可随时查看和分发
- **多环境**：可配置开发 / 测试 / 生产多套 Base URL、全局请求头和环境变量
- **本地私有**：数据保存在本机 SQLite，报告保存在 `reports` 目录，无需联网、无需上传业务数据到第三方

## 目录结构

```text
D:\ai测试平台
├─ backend\              后端（FastAPI + SQLite）
│  ├─ main.py            服务入口与接口
│  ├─ importers.py       接口文档解析（OpenAPI / Swagger / Postman）
│  ├─ ai.py              AI 生成用例 + 规则模式
│  ├─ runner.py          用例执行引擎
│  ├─ reports.py         报告生成
│  └─ templates\         报告 HTML 模板
├─ frontend\             前端页面（原生 HTML/CSS/JS，无需 Node）
├─ samples\              示例接口文档 + 示例后端服务
├─ data\                 数据库文件（自动生成）
├─ reports\              HTML 测试报告（自动生成）
├─ requirements.txt      依赖清单
├─ start.py              启动脚本
├─ install_deps.bat      一键安装依赖到 D:\ai测试平台依赖包
└─ 启动平台.bat           双击启动
```

## 快速开始

1. 依赖已经安装到 `D:\ai测试平台依赖包`，一般不需要再装。如果换电脑或重装，双击 `install_deps.bat` 即可。
2. 双击 `启动平台.bat`，浏览器会自动打开 `http://127.0.0.1:8000`。
3. 想先体验完整流程：先双击 `启动示例接口服务.bat`（在 8080 端口启动一个模拟商城接口），然后在平台里导入 `samples\示例商城接口文档.json`，AI 生成用例后执行，即可看到真实报告。

## 使用流程

1. **导入接口文档**：进入“接口管理”，点击“导入接口文档”，上传 OpenAPI / Swagger / Postman 文件，或直接粘贴内容。
2. **AI 生成用例**：勾选接口（或进入用例管理），点击“AI 生成用例”，选择生成策略。系统会生成可执行的完整用例，包含请求参数、请求体和字段级断言。
3. **人工校验**：AI 生成的是初稿，请按业务规则在“用例管理”中逐条检查、编辑或补充（参考网上调研结论：正常路径 → 参数校验 → 业务逻辑分层 review，效率最高）。
4. **配置环境**：在“系统设置”中把执行环境的 Base URL 改成被测服务地址，全局请求头/变量可按环境配置。
5. **执行用例**：进入“执行与报告”，点击“新建执行”，选择环境和范围，执行结果实时刷新。
6. **查看报告**：执行结束后自动生成 HTML 报告，支持在线查看、另存分发。

## AI 模型配置

在“系统设置 → AI 模型配置”中填写：

- **API 服务地址**：兼容 OpenAI 接口的地址，如 DeepSeek `https://api.deepseek.com/v1`、通义千问兼容地址、本地 Ollama 等
- **API Key**：对应平台申请的密钥
- **模型名称**：如 `deepseek-chat`、`gpt-4o`、`qwen-max` 等
- **温度**：建议 0.1~0.3，测试用例生成要稳定

填写后点“测试连接”验证。**未填写 API Key 时**，平台自动使用“规则模式”，不联网也能生成覆盖必填缺失、边界值、非法枚举等场景的用例。

## 用例与执行说明

- 用例地址支持 `{{base_url}}` 和 `{{变量名}}` 占位，执行时自动替换为环境配置
- 路径参数 `{id}` 或 `:id` 会自动用“路径参数”表格里的值替换
- 需要 Token 的接口，在请求头写 `Authorization: Bearer {{token}}`，把 token 配到环境变量或前置登录用例（可先用登录接口生成一个“获取 token”用例，把返回值手填到环境变量）
- 断言支持：状态码（==、!=、>= 等）、JSON 字段（路径如 `data.id`，支持 `list[0].id`）、响应文本包含/正则、响应时间
- 断言类型 `exists` / `not_exists` / `type` 适合字段级校验，例如创建类接口断言 `data.id` 存在

## 常见问题

**端口被占用**：修改系统环境变量 `AI_TEST_PORT`（如 9000）后重新启动，或先关掉占用 8000 端口的程序。

**内网 HTTPS 证书报错**：在“系统设置”中取消勾选“校验 HTTPS 证书”。

**导入报“无法识别格式”**：确认文件是标准 OpenAPI / Swagger / Postman 格式；公司内网平台导出的 Apifox 文档可先导出为 OpenAPI 格式再导入。

**AI 生成慢或失败**：检查网络、API 地址和 Key；单次生成接口太多时可分批勾选；失败不影响已生成的用例。

**数据在哪**：用例、接口、执行记录都在 `data\app.db`，报告在 `reports\`，备份这两个目录即可迁移。

## 参考资料（网上调研）

- [MeterSphere 支持 AI 生成测试用例（官方实践）](https://blog.fit2cloud.com/?p=1a711e42-04fe-4dce-8196-938071be4021)：OpenAI 兼容模型接入、单条/批量生成、人工校验的最佳实践
- [基于 G-V-R 模型的 LLM 单接口用例生成 7 步法](https://cloud.tencent.com.cn/developer/article/2563607?policyId=1004)：生成-验证-修复闭环，强调接口定义知识库与人工确认
- [手动写接口测试太慢？AI 实操流程与踩坑（腾讯云）](https://cloud.tencent.com.cn/developer/article/2680784?policyId=1003)：喂接口契约而非源码、分层生成、字段级断言、结构化提示词、Token 处理
- [HttpRunner 接口自动化测试平台实战（51Testing）](https://www.51testing.com/html/13/n-7810913.html)：Swagger/Postman 同步、断言自动生成、HTML 报告、CI/CD 集成
- [Apifox 测试用例与 OpenAPI/Swagger 导入](https://apifox.com/blog/features-2025-8/)：一键运行所有用例并查看测试报告的产品形态
- [Pity 开源 API 自动化测试平台（FastAPI）](https://blog.gitcode.com/cb6259afcca0881769f9dcb442a89c5c.html)：FastAPI + SQLAlchemy 后端架构参考
