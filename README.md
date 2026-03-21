# PowerAgent Docs and Demos

这是一个面向电力行业智能体项目的文档与演示材料仓库，当前内容主要包括：

- 电力行业解决方案生成 Agent 的产品文档
- 前后端开发设计与任务拆解文档
- RAG / 知识库 / Agent 规划材料
- PPT 演示材料
- 参考图片与静态网页素材

## 当前技术路线

- 前端：`Vue 3`
- 平台层：`Django + DRF`
- 智能体执行层：`Agent Service + LangGraph`
- 知识库层：`RAGFlow`
- 模型接口：`Qwen`、`MiniMax`

## 重点文档

- [项目文档总览](./项目文档/README.md)
- [PRD](./项目文档/01-产品设计/电力行业解决方案生成Agent_PRD.md)
- [技术架构设计说明书](./项目文档/02-技术设计/电力行业解决方案生成Agent_技术架构设计说明书.md)
- [接口文档](./项目文档/02-技术设计/电力行业解决方案生成Agent_接口文档.md)
- [前端页面详细原型说明](./项目文档/01-产品设计/电力行业解决方案生成Agent_前端页面详细原型说明.md)
- [Vue前端开发任务拆解清单](./项目文档/03-开发计划/电力行业解决方案生成Agent_Vue前端开发任务拆解清单.md)
- [后端开发任务拆解清单](./项目文档/03-开发计划/电力行业解决方案生成Agent_后端开发任务拆解清单.md)
- [Django平台层与AgentService分层设计稿](./项目文档/02-技术设计/Django平台层与AgentService分层设计稿.md)
- [数据库表结构设计草案](./项目文档/02-技术设计/电力行业解决方案生成Agent_数据库表结构设计草案.md)
- [账户与权限体系设计文档](./项目文档/02-技术设计/电力行业解决方案Agent_账户与权限体系设计文档.md)
- [账户与权限体系技术设计稿](./项目文档/02-技术设计/电力行业解决方案Agent_账户与权限体系技术设计稿.md)
- [账户与权限体系开发任务拆解清单](./项目文档/03-开发计划/电力行业解决方案Agent_账户与权限体系开发任务拆解清单.md)

## 目录说明

- `项目文档/`
  - 产品、技术、开发、模板、演示材料等项目文档总目录
- `参考图/`
  - 演示与设计参考图片
- `assets/`
  - 静态网页素材
- `preview/`
  - 预览相关文件
- `测试结果/`
  - Agent 真实测试结果、评审版 HTML/PDF、对比归档
- `backend/`
  - Django 平台层与 Agent Service
- `frontend/`
  - Vue 前端工程

## 说明

当前仓库以文档和演示资料为主，代码实现部分后续可继续补充到独立目录中，例如：

- `frontend/`
- `backend/platform/`
- `backend/agent_service/`

## 当前已生成的项目骨架

- `backend/platform/`
  - Django 平台层骨架
  - 含会话、消息、任务、配置等基础 app

- `backend/agent_service/`
  - Agent Service 骨架
  - 含运行接口、LangGraph 工作流占位、模型适配占位

- `ragflow/`
  - 项目内独立的 RAGFlow 准备环境
  - 含 docker compose、环境变量模板、nginx 配置和启动说明

## 本地启动参考

### Django 平台层

```bash
cd backend/platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# 先确保本机 PostgreSQL 已启动，并存在 power_agent 数据库与用户
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

默认开发数据库：

- `PostgreSQL`

仅在 PostgreSQL 临时不可用时，才允许使用 SQLite 兜底联调：

```bash
cd backend/platform
DJANGO_USE_SQLITE=true python manage.py migrate
DJANGO_USE_SQLITE=true python manage.py runserver 0.0.0.0:8000
```

说明：

- `backend/platform/db.sqlite3` 仅作为本地单人兜底文件，不作为默认开发数据库
- 团队联调、任务回写、会话历史与验收环境统一使用 `PostgreSQL`

### Agent Service

```bash
cd backend/agent_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 9100 --reload
```

### RAGFlow

```bash
cd ragflow
cp .env.example .env
docker compose -f docker-compose.yml up -d
```

默认对接地址：

- `RAGFLOW_BASE_URL=http://127.0.0.1:9381`
- `AGENT_SERVICE_BASE_URL=http://127.0.0.1:9100`

## 数据库说明

- `RAGFlow`：使用其自身环境中的 `MySQL`
- `Django 平台层`：默认使用 `PostgreSQL`
- `SQLite`：仅作为本机临时兜底，不作为默认开发、联调或验收数据库

更多细节见：

- [PostgreSQL本地开发说明](./项目文档/03-开发计划/PostgreSQL本地开发说明.md)
