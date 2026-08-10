# 小说平台 — JMeter 练习环境

一个基于 Flask + MySQL 的 RESTful 小说平台，专为 **JMeter 功能测试 + 压力测试**练习设计。

---

## 快速开始

### 1. 安装依赖

```bash
cd novel-platform
pip install -r requirements.txt
```

### 2. 初始化数据库表

```bash
python init_db.py
```

> 会在你的 `app` 数据库中自动创建 `users`, `novels`, `chapters`, `comments`, `favorites` 五张表。

### 3. 生成种子数据（推荐）

```bash
python seed_data.py
```

生成 50 个用户 + 200 本小说 + 数千章节/评论/收藏，供测试使用。

**测试账号：** `test_001` ~ `test_050`，密码均为 `123456`

### 4. 启动服务（多线程模式）

```bash
python run.py
```

默认监听 `0.0.0.0:5000`，20 个工作线程，连接池 20。

自定义：

```bash
python run.py -p 8080 --threads 50
```

---

## API 接口一览

| 方法 | 路径 | 说明 | 需登录 |
|------|------|------|--------|
| GET | `/api/health` | 健康检查 | ❌ |
| GET | `/api/stats` | 平台统计数据 | ❌ |
| POST | `/api/auth/register` | 注册 | ❌ |
| POST | `/api/auth/login` | 登录，返回 token | ❌ |
| GET | `/api/auth/me` | 获取当前用户 | ✅ |
| GET | `/api/novels` | 小说列表（分页+筛选） | ❌ |
| GET | `/api/novels/categories` | 分类列表 | ❌ |
| GET | `/api/novels/{id}` | 小说详情 | ❌ |
| POST | `/api/novels` | 创建小说 | ✅ |
| PUT | `/api/novels/{id}` | 更新小说 | ✅(作者) |
| DELETE | `/api/novels/{id}` | 删除小说 | ✅(作者) |
| GET | `/api/novels/{id}/chapters` | 章节列表 | ❌ |
| GET | `/api/chapters/{id}` | 章节详情（含正文） | ❌ |
| POST | `/api/novels/{id}/chapters` | 创建章节 | ✅(作者) |
| GET | `/api/novels/{id}/comments` | 评论列表 | ❌ |
| POST | `/api/comments` | 发表评论 | ✅ |
| GET | `/api/favorites` | 我的收藏 | ✅ |
| POST | `/api/favorites` | 添加收藏 | ✅ |
| DELETE | `/api/favorites/{novel_id}` | 取消收藏 | ✅ |

---

## 架构说明

### 多线程支持

```
┌─────────────────────────────────────────────────┐
│                 客户端请求                        │
│  (JMeter 多线程并发)                              │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│           Flask WSGI Server                      │
│         threaded=True  (每请求独立线程)           │
│         默认 20 线程，可配置                      │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│         SQLAlchemy 连接池                        │
│     pool_size=20, max_overflow=10               │
│     线程安全复用连接                              │
└──────────────┬──────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│              MySQL database                      │
│            localhost:3306/app                   │
└─────────────────────────────────────────────────┘
```

- **Flask `threaded=True`**：每个请求分配独立线程
- **连接池 `pool_size=20`**：线程间复用 MySQL 连接
- **`pool_pre_ping=True`**：取出连接前自动检测可用性
- **每个请求内的事务独立隔离**

---

## JMeter 功能测试指南

### 测试计划结构建议

```
Test Plan
├── User Defined Variables
│   ├── host = localhost
│   ├── port = 5000
│   └── base_url = http://${host}:${port}
│
├── Thread Group: 功能测试
│   ├── HTTP Request Defaults (base_url)
│   │
│   ├── [1] 健康检查
│   │   └── GET /api/health
│   │
│   ├── [2] 用户注册
│   │   └── POST /api/auth/register
│   │       Body: {"username":"u_${__time}","password":"123456"}
│   │
│   ├── [3] 用户登录 + 提取 Token
│   │   └── POST /api/auth/login
│   │       Body: {"username":"test_001","password":"123456"}
│   │       JSON Extractor: $.data.token → token
│   │
│   ├── [4] 获取个人信息
│   │   └── GET /api/auth/me
│   │       Header: Authorization: Bearer ${token}
│   │
│   ├── [5] 小说列表
│   │   └── GET /api/novels?page=1&per_page=20
│   │
│   ├── [6] 小说详情
│   │   └── GET /api/novels/{id}
│   │       (使用上一个请求的 $.data.items[0].id)
│   │
│   ├── [7] 章节列表
│   │   └── GET /api/novels/{id}/chapters
│   │
│   ├── [8] 章节详情（含正文）
│   │   └── GET /api/chapters/{id}
│   │
│   ├── [9] 发表评论
│   │   └── POST /api/comments
│   │       Header: Authorization: Bearer ${token}
│   │       Body: {"novel_id":1,"content":"写得真好！"}
│   │
│   ├── [10] 添加收藏
│   │   └── POST /api/favorites
│   │       Header: Authorization: Bearer ${token}
│   │       Body: {"novel_id":1}
│   │
│   ├── [11] 平台统计
│   │   └── GET /api/stats
│   │
│   ├── [12] 创建小说 + 创建章节
│   │   ├── POST /api/novels
│   │   │   Body: {"title":"测试小说","category":"玄幻"}
│   │   │   JSON Extractor: $.data.id → novel_id
│   │   └── POST /api/novels/${novel_id}/chapters
│   │       Body: {"title":"第一章","content":"正文内容..."}
│   │
│   ├── Response Assertion（每个请求）
│   └── View Results Tree（调试用）
```

### 常用断言

```json
// 通用成功断言
响应代码: 200
JSON Path: $.code → 200

// 列表请求断言
JSON Path: $.data.total
JSON Path: $.data.items

// 登录成功断言
JSON Path: $.data.token → NOT NULL
```

### CSV 数据驱动

创建 `users.csv`：

```csv
username,password
test_001,123456
test_002,123456
test_003,123456
```

使用 **CSV Data Set Config** 驱动登录测试。

---

## JMeter 压力测试指南

### 线程组配置建议

| 压测级别 | 线程数 | Ramp-Up | 循环次数 | 预期目标 |
|---------|--------|---------|---------|---------|
| 轻量 | 10 | 5s | 10 | 功能验证 |
| 中等 | 50 | 10s | 50 | 性能基线 |
| 较重 | 100 | 20s | 100 | 系统吞吐量 |
| 高并发 | 200 | 30s | 200 | 极限测试 |
| 尖峰 | 500 | 5s | 50 | 瞬间高负载 |

### 推荐的压测场景

#### 场景 1：混合读写（模拟真实用户）

```
Thread Group: 50 线程, Ramp-Up 20s, 循环 50 次
├── 30% 概率：GET /api/novels（浏览列表）
├── 20% 概率：GET /api/novels/{id}（查看详情）
├── 20% 概率：GET /api/novels/{id}/chapters（看目录）
├── 15% 概率：GET /api/chapters/{id}（看正文）
├── 10% 概率：POST /api/comments（发表评论，需登录）
└──  5% 概率：POST /api/favorites（收藏，需登录）
```

使用 **Throughput Controller** 或 **Switch Controller** 实现概率分配。

#### 场景 2：纯读压测（缓存友好）

```
Thread Group: 100 线程, Ramp-Up 10s, 循环 100 次
└── 仅 GET 请求：
    ├── /api/novels
    ├── /api/novels/{随机ID}
    ├── /api/novels/{随机ID}/chapters
    └── /api/chapters/{随机ID}
```

#### 场景 3：写操作压测

```
Thread Group: 20 线程, Ramp-Up 5s, 循环 50 次
├── 先登录 → 提取 Token
├── 创建小说 → 提取 novel_id
└── 创建章节 → 章节正文 800~1500 字
```

### 监听器配置

- **Aggregate Report** — 查看吞吐量、平均响应时间、错误率
- **Summary Report** — 汇总统计
- **Response Times Over Time** — 响应时间趋势
- **Transactions per Second** — TPS 曲线
- **Active Threads Over Time** — 活跃线程数
- **Graph Results** — 简易图表

### 瓶颈判断

| 指标 | 正常 | 警戒 | 危险 |
|------|------|------|------|
| 平均响应时间 | <200ms | 200~1000ms | >1000ms |
| 95% 响应时间 | <500ms | 500~2000ms | >2000ms |
| 错误率 | 0% | <1% | >5% |
| TPS | - | 稳定 | 大幅下降 |

### 关键观察点

1. **连接池耗尽**：错误中出现 `Can't connect to MySQL server` 或 `Timeout` 时，说明连接池不够大
2. **线程阻塞**：响应时间随并发数线性增长 → 查看 `pool_size` 和 `threads` 参数
3. **大内容响应**：`GET /api/chapters/{id}` 返回完整正文，带宽可能成为瓶颈
4. **写锁争用**：高并发写入时，关注 `POST /api/comments` 和 `POST /api/favorites` 的响应时间

---

## 快速验证

启动服务后：

```bash
# 健康检查
curl http://localhost:5000/api/health

# 登录
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test_001","password":"123456"}'

# 小说列表
curl http://localhost:5000/api/novels?page=1&per_page=10

# 统计数据
curl http://localhost:5000/api/stats
```

---

## 配置调整

编辑 `app/config.py` 中的字段：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `pool_size` | 20 | 连接池大小，压测时可调大 |
| `max_overflow` | 10 | 超出 pool_size 的溢出连接 |
| `pool_timeout` | 30 | 等待连接超时（秒） |
| `pool_recycle` | 300 | 连接回收时间（秒） |

启动时的线程数使用 `--threads` 参数调整：

```bash
python run.py --threads 50        # 50 线程
python run.py -p 8080 --threads 100  # 100 线程 + 8080 端口
```