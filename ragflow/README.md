# RAGFlow Local Deployment for PowerAgent

这个目录提供一套项目内独立的 RAGFlow 准备环境，目的是：

- 不改动外部旧的 `/Users/Jarod/ragflow` 环境
- 先在当前项目仓库中保留一套可启动、可联调的知识库层部署模板
- 后续让 `backend/agent_service` 直接对接本目录启动的 RAGFlow

## 目录内容

- `.env.example`
  - 环境变量模板
- `docker-compose.yml`
  - RAGFlow 主服务
- `docker-compose-base.yml`
  - Elasticsearch / MySQL / Redis / MinIO / Infinity 依赖
- `nginx/`
  - 官方 nginx 配置副本
- `init.sql`
  - 官方初始化 SQL
- `infinity_conf.toml`
  - Infinity 配置

## 默认端口

为了避免和你外部历史环境冲突，这里默认使用一组项目内端口：

- `RAGFlow Web / API Gateway`: `9381`
- `Elasticsearch`: `1201`
- `MySQL`: `5456`（宿主机映射）
- `Redis`: `6380`
- `MinIO API`: `9002`
- `MinIO Console`: `9003`

说明：

- `SVR_HTTP_PORT=9381`
  - 映射到容器内部 `80`，用于浏览器访问和统一 API 入口
- `MYSQL_PORT=3306`
  - 这是容器内部给 RAGFlow 连接 MySQL 使用的端口
- `MYSQL_EXPOSE_PORT=5456`
  - 这是宿主机映射端口，方便你从本机外部调试 MySQL

## 启动方式

```bash
cd ragflow
cp .env.example .env
docker compose -f docker-compose.yml up -d
```

## 停止方式

```bash
cd ragflow
docker compose -f docker-compose.yml down
```

注意：

```bash
docker compose -f docker-compose.yml down -v
```

会清掉 volumes 和数据，不建议在首次准备阶段使用。

## 与 Agent Service 对接

如果你使用这个项目内 RAGFlow，请把以下配置写入：

`backend/agent_service/.env`

```env
RAGFLOW_BASE_URL=http://127.0.0.1:9381
RAGFLOW_API_KEY=你的RAGFlow API Key
RAGFLOW_DATASET_PAPERS=
RAGFLOW_DATASET_STANDARDS=
RAGFLOW_DATASET_CASES=
RAGFLOW_DATASET_SOLUTIONS=
```

## 推荐使用顺序

1. 启动 Docker Desktop
2. 在当前目录复制 `.env.example` 为 `.env`
3. 启动 RAGFlow
4. 浏览器打开 `http://127.0.0.1:9381`
5. 在 UI 里配置模型和知识库
6. 再回填 `backend/agent_service/.env`
7. 最后做检索联调
