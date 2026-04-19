# 记账智能体

一个基于 LangChain + LangGraph 构建的多模态记账智能体骨架。当前默认将账单数据存储在本地 JSON 文件中，方便先在本地调试和试发布，后续可替换为 Java 后端 API 或数据库适配器。

## 功能特性

- 自然语言添加账单
- 查询最近账单
- 按分类或收支类型汇总统计
- 直接接收消息附图，判断图片是否和记账有关
- 对相关图片自动抽取账单候选信息，信息足够时自动调用记账工具
- 关键信息不足时，只追问缺失字段，不走草稿确认链
- 使用显式 LangGraph 流程和双 `ToolNode`
- 本地 CLI 默认使用内存 checkpointer
- LangSmith/LangGraph 发布入口已通过 `langgraph.json` 暴露

## 项目结构

```text
agent/
  account_agent/
    config/       # 配置
    graph/        # LangGraph 流程与节点
    service/      # 账本与图片分析服务
    storage/      # 存储层
    tools/        # 工具函数
  data/           # 本地账本目录
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

## 示例指令

- `记一笔午饭，花了 28 元，分类餐饮`
- `帮我记一笔工资收入 12000 元，分类工资`
- `查询最近 5 笔流水`
- `统计一下餐饮支出`
- `按收入类型汇总一下`

多模态图片链路请在 LangSmith / Studio / API 调用中测试，给用户消息直接附图即可，不再把本地文件路径作为正式输入方式。

## 推荐配置

当前默认示例已经改成“一把 key 跑文本和视觉”：

- 文本模型：`qwen3.5-flash`
- 视觉模型：`qwen3.5-flash`
- 接口：阿里百炼 OpenAI-compatible

也就是说，通常你只需要在 `.env` 里填写：

```env
ACCOUNT_AGENT_API_KEY=你的百炼API Key
```

默认就会同时用于文本模型和视觉模型。

## 多模态图片记账说明

- 第一版只处理消息附图，不支持本地路径、PDF、HTTP 上传
- agent 会先判断图片是否和记账有关
- 若图片无关：直接回复不记账
- 若图片相关且 `amount`、`kind`、`category` 齐全：自动调用 `add_bill`
- 若图片相关但关键信息不足：只追问缺失字段
- 默认视觉模型示例是 `qwen3.5-flash`
- 默认文本模型示例是 `qwen3.5-flash`
- 默认情况下文本和视觉共用同一把 `ACCOUNT_AGENT_API_KEY`
- 只有当你想让视觉模型走另一家服务时，才需要额外配置 `ACCOUNT_AGENT_VISION_API_KEY`

## 发布到 LangSmith 前

- 确保仓库里包含 `langgraph.json`
- 在 LangSmith 部署环境中至少配置 `ACCOUNT_AGENT_API_KEY`
- 若你不使用默认百炼地址，再补充配置 `ACCOUNT_AGENT_BASE_URL`
- 若多模态模型与主模型不同，补充配置 `ACCOUNT_AGENT_VISION_MODEL`、`ACCOUNT_AGENT_VISION_API_KEY`、`ACCOUNT_AGENT_VISION_BASE_URL`
- 如需本地 tracing，可配置 `LANGCHAIN_TRACING_V2`、`LANGCHAIN_API_KEY`、`LANGCHAIN_PROJECT`
- 生产部署时建议把账本存储替换为后端 API 或数据库，不要长期依赖本地文件

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

- 将 `JsonLedgerStore` 替换为 HTTP 客户端，对接 Java 后端
- 为账本存储增加数据库或后端 API 适配层
- 为多模态分析服务接入更稳定的视觉模型或企业 OCR
- 增加更多工具，如删除账单、修改账单、月报、预算提醒
- 添加 FastAPI 或 Flask API 层，供外部系统集成
