# 记账智能体

一个基于 LangChain + LangGraph 构建的多模态记账智能体骨架。当前正式记账、查询、统计链路已经按 Java 后端 API 方式组织，Python 侧主要负责多模态理解、工具编排和统一对外接口。

## 功能特性

- 自然语言添加账单
- 查询最近账单
- 按分类或收支类型汇总统计
- 直接接收消息附图，判断图片是否和记账有关
- 对相关图片自动抽取账单候选信息，信息足够时自动调用记账工具
- 关键信息不足时，只追问缺失字段，不走草稿确认链
- 使用显式 LangGraph 流程和双 `ToolNode`
- 本地 CLI / API 默认使用 SQLite checkpointer
- LangSmith/LangGraph 发布入口已通过 `langgraph.json` 暴露

## 项目结构

```text
agent/
  account_agent/
    api/          # FastAPI 联调接口
    config/       # 配置
    graph/        # LangGraph 流程与节点
    service/      # 后端服务封装与图片分析服务
    tools/        # 工具函数
  tests/          # 单元测试
  .env.example    # 环境变量模板
  .gitignore
  langgraph.json  # LangSmith/LangGraph 部署配置
  main.py         # CLI 入口
  pyproject.toml
  README.md
```

## 快速开始

1. 同步依赖：

```bash
uv sync
```

2. 复制环境变量模板并填入你的 key：

```bash
Copy-Item .env.example .env
```

3. 启动 CLI：

```bash
uv run python main.py
```

4. 本地启动 LangGraph dev server：

```bash
uv run langgraph dev --no-browser
```

如果提示找不到 `langgraph` 命令，请先安装 `langgraph-cli`。

5. 启动前端联调 API：

```bash
uv run accounting-agent-api
```

默认会启动在 `http://127.0.0.1:8000`。

## 示例指令

- `记一笔午饭，花了 28 元，分类餐饮`
- `帮我记一笔工资收入 12000 元，分类工资`
- `查询最近 5 笔流水`
- `统计一下餐饮支出`
- `按收入类型汇总一下`

多模态图片链路请在 LangSmith / Studio / API 调用中测试，给用户消息直接附图即可，不再把本地文件路径作为正式输入方式。

## API 联调

当前已经提供 FastAPI 接口，前端可以直接请求 Python 服务：

- `GET /api/v1/health`
- `POST /api/v1/agent/chat`
- `POST /api/v1/chat/stream`
- `GET /api/v1/chat/history/{thread_id}`

文本请求示例：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/agent/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"thread_id\":\"web-user-1\",\"message\":\"工资发了2000\"}"
```

正式流式接口示例：

```bash
curl -N -X POST http://127.0.0.1:8000/api/v1/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"thread_id\":\"conv_user_8892\",\"message\":\"识别这张图片并记账\",\"stream\":true,\"attachments\":[{\"type\":\"image\",\"url\":\"https://oss.example.com/account/receipt.jpg\"}]}"
```

推荐的正式上传链路：

- 前端先请求 Spring
- Spring 上传附件到 OSS
- Spring/前端拿到图片 URL
- 前端再把 URL 放进 `attachments` 发给 Python Agent

当前 SSE 事件类型：

- `info`：开始思考提示
- `tool`：工具调用信息
- `delta`：当前回复片段
- `final`：最终结构化结果
- `[DONE]`：本轮结束

说明：

- 目前这层 SSE 已符合前端事件流协议，但 agent 内部仍以阻塞图执行为主，所以 `delta` 现在是“消息块级流”，还不是逐 token 真流。
- 会话历史当前默认落盘到 SQLite checkpoint，重启进程后线程记忆仍可保留。
- Python Agent 侧已经不再负责文件上传与文件落盘，附件由前端通过 URL 引用。
- Python Agent 侧正式账务工具默认直接调用 Java 后端接口。

## 推荐配置

当前默认示例已经改成“一套模型配置同时跑文本和图片分析”：

- 统一模型：`qwen3.5-flash`
- 接口：阿里百炼 OpenAI-compatible

也就是说，通常你只需要在 `.env` 里填写：

```env
ACCOUNT_AGENT_API_KEY=你的百炼API Key
ACCOUNT_AGENT_TEMPERATURE=0
ACCOUNT_AGENT_CHECKPOINT_PATH=./runtime_data/checkpoints.sqlite
ACCOUNT_AGENT_SERVER_BASE_URL=http://127.0.0.1:8080/api/v1
ACCOUNT_AGENT_SERVER_AUTH_MODE=bearer
ACCOUNT_AGENT_SERVER_TOKEN=你的后端登录 token
```

默认同一套模型配置会同时用于文本对话和图片分析，账务工具则直接走 Java 后端。

- `ACCOUNT_AGENT_TEMPERATURE` 主要控制主助手的工具决策稳定性，建议保持较低
- `ACCOUNT_AGENT_CHECKPOINT_PATH` 用来指定 SQLite 会话文件位置；相对路径会落到 `agent/runtime_data/` 这类项目目录下

## 多模态图片记账说明

- 第一版只处理消息附图，不支持本地路径、PDF、HTTP 上传
- agent 会先判断图片是否和记账有关
- 若图片无关：直接回复不记账
- 若图片相关且 `amount`、`kind`、`category` 齐全：自动调用 `add_bill`
- 若图片相关但关键信息不足：只追问缺失字段
- 默认文本和图片分析都使用 `ACCOUNT_AGENT_MODEL`
- 默认文本和图片分析都使用同一把 `ACCOUNT_AGENT_API_KEY`

## 发布到 LangSmith 前

- 确保仓库里包含 `langgraph.json`
- 在 LangSmith 部署环境中至少配置 `ACCOUNT_AGENT_API_KEY`
- 若你不使用默认百炼地址，再补充配置 `ACCOUNT_AGENT_BASE_URL`
- 至少配置 `ACCOUNT_AGENT_SERVER_BASE_URL`
- 若后端接口需要鉴权，再补充 `ACCOUNT_AGENT_SERVER_AUTH_MODE` 与 `ACCOUNT_AGENT_SERVER_TOKEN`
- 如需本地 tracing，可配置 `LANGCHAIN_TRACING_V2`、`LANGCHAIN_API_KEY`、`LANGCHAIN_PROJECT`

## 运行检查

语法检查：

```bash
uv run python -m compileall account_agent main.py tests
```

运行测试：

```bash
uv run python -m unittest discover -s tests
```

## 扩展方向

- 为后端接口增加更完整的认证透传与重试策略
- 为分类、统计等服务增加更细粒度的缓存策略
- 为多模态分析服务接入更稳定的视觉模型或企业 OCR
- 增加更多工具，如删除账单、修改账单、月报、预算提醒
- 添加 FastAPI 或 Flask API 层，供外部系统集成
