# PostgreSQL 本地开发说明

本文档用于说明当前项目的本地数据库默认约定、初始化步骤及 SQLite 兜底边界。

## 默认约定

- `Django 平台层` 默认使用 `PostgreSQL`
- `RAGFlow` 继续使用自身环境内的 `MySQL`
- `SQLite` 仅作为本机临时兜底联调方案，不作为团队默认开发数据库

推荐原因：

- 平台层涉及 `会话 / 消息 / 任务 / 审计 / 配置` 等长期演进能力
- 结果回写与证据卡、参数、元数据等字段包含大量 JSON 结构
- `PostgreSQL` 更适合作为 Django 平台层的默认数据库

## 本机当前推荐配置

项目默认使用以下数据库连接：

```env
POSTGRES_NAME=power_agent
POSTGRES_USER=power_agent
POSTGRES_PASSWORD=power_agent
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
DJANGO_USE_SQLITE=false
```

对应配置文件：

- [backend/platform/.env](/Users/Jarod/PPT/backend/platform/.env)
- [backend/platform/.env.example](/Users/Jarod/PPT/backend/platform/.env.example)

## PostgreSQL 初始化步骤

### 1. 启动 PostgreSQL

如果使用 Homebrew 安装：

```bash
brew services start postgresql@16
pg_isready
```

## 2. 创建项目角色与数据库

如果本机当前管理用户可直接连接 `postgres`，执行：

```bash
psql postgres
```

进入后执行：

```sql
CREATE ROLE power_agent LOGIN PASSWORD 'power_agent';
CREATE DATABASE power_agent OWNER power_agent;
\q
```

如果角色或数据库已存在，可跳过。

## 3. 验证项目连接

```bash
PGPASSWORD=power_agent psql -h 127.0.0.1 -U power_agent -d power_agent -c '\conninfo'
```

成功时应看到：

- 当前数据库：`power_agent`
- 当前用户：`power_agent`

## 4. Django 迁移

```bash
cd /Users/Jarod/PPT/backend/platform
./.venv/bin/python manage.py migrate
```

## 5. 启动 Django

```bash
cd /Users/Jarod/PPT/backend/platform
./.venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

## 6. 最小验证

```bash
curl -sS http://127.0.0.1:8000/api/v1/meta/options
curl -sS -X POST http://127.0.0.1:8000/api/v1/conversations -H 'Content-Type: application/json' -d '{"title":"PostgreSQL验证"}'
```

## SQLite 兜底边界

只有在以下情况，才建议启用 SQLite：

- PostgreSQL 本机临时不可用
- 单人快速调试某个不依赖共享数据的页面或接口
- 临时验证迁移外的轻量功能

兜底启动方式：

```bash
cd /Users/Jarod/PPT/backend/platform
DJANGO_USE_SQLITE=true ./.venv/bin/python manage.py migrate
DJANGO_USE_SQLITE=true ./.venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload
```

请注意：

- `backend/platform/db.sqlite3` 不作为团队联调数据库
- 不应基于 SQLite 结果进行验收判断
- 不应用于多服务、多用户或需要结果持久回写的一体化测试

## 推荐的团队约定

建议团队统一遵循：

1. `本地默认数据库 = PostgreSQL`
2. `平台联调与验收 = PostgreSQL`
3. `SQLite = 仅兜底，不作为主路径`
4. `RAGFlow 的 MySQL 与平台层 PostgreSQL 分层管理，不强行统一`
