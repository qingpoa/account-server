# 记账智能体

一个基于 LangChain + LangGraph 构建的轻量级记账智能体演示。当前默认将账单数据存储在本地 JSON 文件中，方便先在本地调试和试发布，后续可替换为 Java 后端 API 或数据库适配器。

## 功能特性

- 自然语言添加账单
- 查询最近账单
- 按分类或收支类型汇总统计
- 使用 LangChain agent + LangGraph 线程记忆
- 本地 CLI 默认使用内存 checkpointer
- LangSmith/LangGraph 发布入口已通过 `langgraph.json` 暴露

## 项目结构

```text
agent/
  account_agent/
    config/       # 配置
    graph/        # agent 构建与部署入口
    service/      # 业务逻辑
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

## 发布到 LangSmith 前

- 确保仓库里包含 `langgraph.json`
- 在 LangSmith 部署环境中配置 `DEEPSEEK_API_KEY`
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
- 增加更多工具，如删除账单、修改账单、月报、预算提醒
- 添加 FastAPI 或 Flask API 层，供外部系统集成
