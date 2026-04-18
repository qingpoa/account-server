# 记账智能体

一个基于 LangChain + LangGraph 构建的轻量级记账智能体演示。账单数据存储在本地 JSON 文件中，后续可轻松替换为 Java 后端 API 或数据库适配器。

## 功能特性

- 自然语言添加账单
- 查询最近账单
- 按分类或收支类型汇总统计
- LangGraph 流程：`START -> assistant -> tools -> assistant -> END`
- 基于 LangGraph checkpointer 实现会话级别内存

## 项目结构

```text
agent/
  account_agent/
    config/       # 配置
    graph/        # LangGraph 流程定义
    service/      # 业务逻辑
    storage/      # 存储层
    tools/        # 工具函数
  data/           # JSON 数据存储目录
  tests/          # 单元测试
  .env.example    # 环境变量模板
  .gitignore
  main.py         # CLI 入口
  pyproject.toml
  README.md
```

## 快速开始

1. 创建并激活虚拟环境。
2. 安装依赖：

```bash
pip install -e .
```

3. 复制环境变量模板并填入你的 key：

```bash
Copy-Item .env.example .env
```

4. 启动 CLI：

```bash
python main.py
```

## 示例指令

- `记一笔午饭，花了 28 元，分类餐饮`
- `帮我记一笔工资收入 12000 元，分类工资`
- `查询最近 5 笔流水`
- `统计一下餐饮支出`
- `按收入类型汇总一下`

## 运行检查

语法检查：

```bash
python -m compileall account_agent main.py tests
```

运行测试：

```bash
python -m unittest discover -s tests
```

## 扩展方向

- 将 `JsonLedgerStore` 替换为 HTTP 客户端，对接 Java 后端
- 添加持久化 checkpointer，实现长期会话记忆
- 增加更多工具，如删除账单、修改账单、月报、预算提醒
- 添加 FastAPI 或 Flask API 层，供外部系统集成
