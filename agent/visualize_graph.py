"""
Graph Visualization Script
===========================
可视化 agent graph 结构，不运行任何模型。

Usage:
    python visualize_graph.py --mermaid   # Mermaid 代码
    python visualize_graph.py --png        # 生成 PNG 并打开
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def get_graph():
    """获取 graph 实例，不绑定实际模型"""
    from account_agent.graph import builder
    from account_agent.tools import get_tools, get_analysis_tools
    from account_agent.service import ImageAnalysisService

    mock_tools = get_tools()
    mock_analysis_tools = get_analysis_tools(ImageAnalysisService(llm=None))

    original_get_tools = builder.get_tools
    original_get_analysis = builder.get_analysis_tools

    builder.get_tools = lambda: mock_tools
    builder.get_analysis_tools = lambda svc: mock_analysis_tools

    graph = builder.build_graph(model={"model": "mock"})

    builder.get_tools = original_get_tools
    builder.get_analysis_tools = original_get_analysis

    return graph


def show_graph():
    """生成 PNG 并保存"""
    graph = get_graph()
    g = graph.get_graph()
    img_bytes = g.draw_mermaid_png()

    output_path = Path(__file__).parent / "graph.png"
    with open(output_path, "wb") as f:
        f.write(img_bytes)

    import os, webbrowser, sys as _sys
    if _sys.platform == "win32":
        os.startfile(output_path)
    else:
        webbrowser.open(f"file://{output_path}")

    print(f"Graph saved to: {output_path}")


def print_mermaid():
    """打印 Mermaid 代码"""
    graph = get_graph()
    g = graph.get_graph()
    print(g.draw_mermaid())


def main():
    parser = argparse.ArgumentParser(description="可视化 agent graph 结构")
    parser.add_argument("--mermaid", action="store_true", help="显示 Mermaid 代码")
    args = parser.parse_args()

    if args.mermaid:
        print_mermaid()
    else:
        show_graph()


if __name__ == "__main__":
    main()
