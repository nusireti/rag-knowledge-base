"""
Agent 工具集 - 高性能版
每次提问最多 2 次 LLM 调用（从 4 次优化）
"""

import re
import json
import sys
import os
import requests
from typing import Optional

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.config import settings
from app.logger import logger
from app.rag.engine import get_llm, clean_output, format_docs, get_vector_store


# ============ 工具函数 ============

def web_search(query: str) -> str:
    """联网搜索（天气优先走 API，搜索走 DDGS）"""
    import requests
    headers = {"User-Agent": "Mozilla/5.0"}

    # 检测天气查询
    weather_keywords = ["天气", "气温", "下雨", "下雪", "晴", "阴", "weather", "temperature"]
    is_weather = any(kw in query for kw in weather_keywords)

    if is_weather:
        # 提取城市名
        city_match = re.search(r'[一-鿿]+', query)
        if city_match:
            city = city_match.group()
            try:
                # wttr.in 需要 curl User-Agent 才返回纯文本
                curl_headers = {"User-Agent": "curl/8.0"}
                resp = requests.get(
                    f"https://wttr.in/{city}?format=%C+%t+%h+%w&lang=zh",
                    headers=curl_headers, timeout=10,
                )
                if resp.status_code == 200 and resp.text.strip():
                    return f"天气信息: {city} {resp.text.strip()}"
            except Exception:
                pass

        # 如果中文城市名没结果，试试拼音/英文
        if False:  # 占位，后续可加拼音转换
            pass

    # DDGS 通用搜索
    try:
        from ddgs import DDGS
        with DDGS(timeout=8) as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if results:
            return "\n\n".join(
                f"[{i+1}] {r['title']}\n{r['href']}\n{r['body']}"
                for i, r in enumerate(results)
            )
    except Exception:
        pass

    # Bing 兜底
    try:
        r = requests.get(f"https://www.bing.com/search?q={query}", headers=headers, timeout=8)
        if r.status_code == 200:
            titles = re.findall(r'<h2><a[^>]*>(.*?)</a></h2>', r.text)
            if titles:
                return "\n".join(f"[{i+1}] {t}" for i, t in enumerate(titles[:5]))
    except Exception:
        pass

    return ""


def calculator(expr: str) -> str:
    """安全计算器"""
    try:
        cleaned = re.sub(r'[^0-9+\-*/().,%^eE\s]', '', expr.replace('^', '**'))
        if not cleaned:
            return ""
        import math
        ns = {k: getattr(math, k) for k in dir(math) if not k.startswith('_')}
        ns.update({"abs": abs, "round": round, "int": int, "float": float})
        return str(eval(cleaned, {"__builtins__": {}}, ns))
    except Exception:
        return ""


def get_time(_: str = "") -> str:
    import datetime
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============ Agent（简洁版） ============

SYSTEM_PROMPT_AGENT = """你是一个智能助手，可以使用工具来回答问题。

## 可用工具
- web_search(query)：搜索互联网（天气、新闻等实时信息）
- calculator(expression)：数学计算，如 "2**16" "sqrt(144)"
- get_time()：获取当前时间。用户问"现在几点""今天几号"等必须用此工具
- knowledge_base(query)：从知识库检索文档内容

## 核心规则
1. 问时间日期 → 必须用 get_time 工具
2. 问天气新闻等实时信息 → 用 web_search
3. 数学计算 → 用 calculator
4. 其他 → 直接回答

## 输出格式
需要工具时回复: TOOL:工具名|参数
不需要工具时直接回复答案。"""


def ask_agent(question: str, vector_dir: str = None, chat_history: list = None) -> dict:
    """
    高效 Agent：
    第1步：LLM 判断是否需要工具 + 给出参数（1次调用）
    第2步：执行工具（如有）
    第3步：生成最终回答（1次调用）
    """
    llm = get_llm(streaming=False)

    # ---- 第1步：LLM 决策（一次调用完成） ----
    history_str = ""
    if chat_history and len(chat_history) > 6:
        for m in chat_history[-6:]:
            history_str += f"{'用户' if m['role']=='user' else 'AI'}: {m['content']}\n"

    prompt = f"""{SYSTEM_PROMPT_AGENT}

对话历史：
{history_str}

用户问题: {question}

请决定是否需要使用工具。"""
    raw = clean_output(llm.invoke(prompt).content)

    # ---- 解析 LLM 输出 ----
    answer = ""
    mode = "direct"

    if raw.strip().upper().startswith("TOOL:"):
        # 解析 TOOL:工具名|参数
        try:
            parts = raw.strip().split(":", 1)[1].strip()
            tool_name, tool_input = parts.split("|", 1)
            tool_name = tool_name.strip().lower()
            tool_input = tool_input.strip().strip('"\'')
        except (ValueError, IndexError):
            tool_name = ""
            tool_input = ""

        # ---- 第2步：执行工具 ----
        tool_result = ""
        if tool_name == "web_search":
            tool_result = web_search(tool_input or question)
            mode = "web"
        elif tool_name == "calculator":
            tool_result = calculator(tool_input)
            mode = "tool"
        elif tool_name == "get_time":
            tool_result = get_time()
            mode = "tool"
        elif tool_name in ("knowledge_base", "kb"):
            if vector_dir and os.path.exists(vector_dir) and any(os.scandir(vector_dir)):
                vs = get_vector_store(vector_dir)
                retriever = vs.as_retriever(
                    search_type=settings.RETRIEVAL_SEARCH_TYPE,
                    search_kwargs={"k": settings.RETRIEVAL_K},
                )
                docs = retriever.invoke(tool_input or question)
                tool_result = format_docs(docs) if docs else "知识库中未找到相关信息"
                mode = "rag"
            else:
                tool_result = "知识库未就绪"
                mode = "direct"

        if not tool_result:
            tool_result = "未获取到有效信息"

        # ---- 第3步：LLM 生成最终回答 ----
        final_prompt = f"""用户问题: {question}
使用的工具: {tool_name}
工具结果: {tool_result}

请根据工具结果，用中文直接回答用户问题。简洁清晰。"""
        answer = clean_output(llm.invoke(final_prompt).content)

    else:
        # 直接回答
        answer = clean_output(raw)
        mode = "direct"

    return {"answer": answer, "mode": mode}
