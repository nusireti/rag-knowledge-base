"""
Agent 工具集
为 AI 提供：知识库检索、联网搜索、计算器等工具
"""

import re
import json
from typing import Optional, List, Dict, Any

from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document

from config import RETRIEVAL_K, RETRIEVAL_SEARCH_TYPE
from query import load_vector_store, format_docs, get_llm


# ============ 工具 1: RAG 知识库检索 ============

def create_rag_tool(vector_dir: str) -> Tool:
    """
    创建 RAG 知识库检索工具

    参数:
        vector_dir: 当前知识库的向量数据库目录
    """
    def search_knowledge_base(query: str) -> str:
        """
        从知识库中检索与问题相关的文档内容。
        当你需要基于用户上传的文档来回答问题时使用这个工具。
        """
        try:
            vs = load_vector_store(vector_dir)
            retriever = vs.as_retriever(
                search_type=RETRIEVAL_SEARCH_TYPE,
                search_kwargs={"k": RETRIEVAL_K},
            )
            docs = retriever.invoke(query)
            if not docs:
                return "知识库中没有找到相关信息。"
            return format_docs(docs)
        except Exception as e:
            return f"[知识库检索出错: {e}]"

    return Tool(
        name="knowledge_base_search",
        description="从本地知识库中检索与问题相关的文档内容。输入一个搜索查询，返回匹配的文档片段。适合回答关于已上传文档的问题。",
        func=search_knowledge_base,
    )


# ============ 工具 2: 联网搜索 ============

def create_web_search_tool() -> Tool:
    """创建联网搜索工具"""
    def web_search(query: str) -> str:
        """
        搜索互联网获取最新信息。
        当问题涉及实时信息、新闻、或知识库中没有的内容时使用。
        """
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for i, r in enumerate(ddgs.text(query, max_results=5)):
                    results.append(f"[{i+1}] {r['title']}\n{r['href']}\n{r['body']}")
            if not results:
                return "联网搜索没有找到相关结果。"
            return "\n\n---\n\n".join(results)
        except Exception as e:
            return f"[联网搜索出错: {e}]"

    return Tool(
        name="web_search",
        description="搜索互联网获取最新信息。输入搜索关键词，返回网页标题、链接和摘要。适合获取实时信息、新闻、或知识库未覆盖的内容。",
        func=web_search,
    )


# ============ 工具 3: 计算器 ============

def create_calculator_tool() -> Tool:
    """创建计算器工具"""
    def calculator(expression: str) -> str:
        """
        执行数学计算。输入数学表达式，返回计算结果。
        支持：+ - * / ** % 以及 math 模块的函数
        """
        try:
            # 安全计算：只允许数字和运算符
            safe_chars = set("0123456789.+-*/%()[]eE ")
            cleaned = "".join(c for c in expression if c in safe_chars or c in ",^")
            cleaned = cleaned.replace("^", "**").replace(",", ".")

            if not cleaned:
                return "请输入有效的数学表达式"

            import math
            namespace = {
                "math": math,
                "abs": abs, "round": round, "int": int, "float": float,
                "pi": math.pi, "e": math.e,
                "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
                "pow": pow, "sum": sum,
            }
            result = eval(cleaned, {"__builtins__": {}}, namespace)
            return f"计算结果: {result}"
        except Exception as e:
            return f"[计算错误: {e}]"

    return Tool(
        name="calculator",
        description="执行数学计算。输入数学表达式如 '2 ** 10' 或 'sqrt(144) + 3.14'，返回计算结果。",
        func=calculator,
    )


# ============ 工具 4: 获取当前时间 ============

def create_time_tool() -> Tool:
    """获取当前时间"""
    import datetime

    def get_time(_: str = "") -> str:
        now = datetime.datetime.now()
        return f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)"

    return Tool(
        name="current_time",
        description="获取当前的日期和时间。当你需要知道现在是什么时间时使用。",
        func=get_time,
    )


# ============ Agent 执行器 ============

SYSTEM_PROMPT_AGENT = """你是一个智能助手，可以访问以下工具来回答问题。

## 工具说明

1. **knowledge_base_search**: 检索本地知识库中的文档内容
2. **web_search**: 搜索互联网获取最新信息
3. **calculator**: 执行数学计算
4. **current_time**: 获取当前时间

## 使用规则

- 如果问题是关于已上传文档的，优先使用 knowledge_base_search
- 如果问题涉及实时信息或新闻，使用 web_search
- 如果问题需要数学计算，使用 calculator
- 可以组合使用多个工具来获得完整答案
- 用中文回答，简洁清晰
"""


def create_agent(vector_dir: str = None):
    """
    创建 Agent（使用 ReAct 模式）

    参数:
        vector_dir: 知识库向量库目录（None = 纯联网模式）
    """
    # 收集工具
    tools = []

    # RAG 工具（如果有向量库）
    if vector_dir:
        import os
        if os.path.exists(vector_dir) and any(os.scandir(vector_dir)):
            tools.append(create_rag_tool(vector_dir))

    # 通用工具
    tools.append(create_web_search_tool())
    tools.append(create_calculator_tool())
    tools.append(create_time_tool())

    return tools


def run_agent(question: str, tools: List[Tool], chat_history: List[dict] = None) -> str:
    """
    运行 Agent 回答问题

    这是一个简化版 Agent：让 LLM 决定用哪个工具，解析结果后继续。
    由于 LangChain 的 AgentExecutor 在不同版本间 API 变化较大，
    这里使用手动循环方式实现 ReAct 模式。
    """
    llm = get_llm(streaming=False)

    # 构建工具描述
    tool_descriptions = "\n\n".join([
        f"## {t.name}\n{t.description}\n使用格式: {t.name}(输入)"
        for t in tools
    ])

    # 构建对话历史
    history_str = ""
    if chat_history and len(chat_history) > 6:
        recent = chat_history[-6:]
        for msg in recent:
            role = "用户" if msg["role"] == "user" else "AI"
            history_str += f"{role}: {msg['content']}\n"

    # 初始提示
    prompt = f"""{SYSTEM_PROMPT_AGENT}

## 可用工具
{tool_descriptions}

## 使用示例
要搜索知识库，回复：
THOUGHT: 我需要查看文档中是否有相关信息
ACTION: knowledge_base_search
INPUT: 搜索关键词

要搜索网络，回复：
THOUGHT: 这个问题需要最新信息
ACTION: web_search
INPUT: 搜索关键词

得到结果后，回复最终答案：
OBSERVATION: (工具返回的结果)
FINAL: (你的最终回答)

---

对话历史：
{history_str}

用户问题: {question}

请根据问题选择合适的工具。如果不需要工具，直接回答。
"""
    # 第一阶段：让 LLM 决定是否使用工具
    response = llm.invoke(prompt).content

    # 解析工具调用
    tool_pattern = re.search(r"ACTION:\s*(\w+)\s*\nINPUT:\s*(.+)", response)
    if tool_pattern:
        tool_name = tool_pattern.group(1).strip()
        tool_input = tool_pattern.group(2).strip()

        # 查找并执行工具
        selected_tool = None
        for t in tools:
            if t.name == tool_name:
                selected_tool = t
                break

        if selected_tool:
            try:
                tool_result = selected_tool.func(tool_input)

                # 第二阶段：让 LLM 基于工具结果生成最终回答
                final_prompt = f"""{SYSTEM_PROMPT_AGENT}

原始问题: {question}
使用的工具: {tool_name}
工具输入: {tool_input}
工具返回结果:
{tool_result}

请基于工具返回的结果回答问题。如果工具没有找到相关信息，如实告知。
用中文回答，简洁清晰。
"""
                final_answer = llm.invoke(final_prompt).content
                return final_answer
            except Exception as e:
                return f"[工具执行出错: {e}]"
        else:
            return f"[未找到工具: {tool_name}]"
    else:
        # 没有工具调用，直接返回 LLM 的回答（去掉 THOUGHT/FINAL 前缀）
        clean = re.sub(r"^(THOUGHT|FINAL|思考|最终回答):\s*", "", response, flags=re.MULTILINE)
        return clean.strip()


def ask_agent(question: str, vector_dir: str = None, chat_history: list = None) -> dict:
    """
    Agent 模式问答

    返回: {"answer": str, "mode": "rag|web|hybrid"}
    """
    tools = create_agent(vector_dir)
    answer = run_agent(question, tools, chat_history)

    # 判断使用了哪些工具
    mode = "direct"
    tool_names = [t.name for t in tools]
    if any(t.name in answer for t in tools if t.name == "knowledge_base_search"):
        mode = "rag"
    if "web_search" in answer or any(s in answer for s in ["搜索结果", "互联网", "据搜索"]):
        mode = "web"

    return {
        "answer": answer,
        "mode": mode,
    }
