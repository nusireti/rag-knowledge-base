"""
RAG 知识库配置文件
根据自己的需求修改这里的配置
"""

import os

# ============ 路径配置 ============
# 文档存放目录（把 PDF/TXT/Markdown 放这里）
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
# 向量数据库存储位置
VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "vector_store")

# ============ Embedding 模型配置 ============
# 可选：
#   - "local" : 使用本地 Sentence Transformer（免费，无需联网）
#   - "openai" : 使用 OpenAI Embedding（效果更好，需要 API Key）
EMBEDDING_PROVIDER = "local"

# 本地 Embedding 模型（EMBEDDING_PROVIDER="local" 时生效）
# 中文推荐：BAAI/bge-small-zh-v1.5（轻量）或 BAAI/bge-large-zh-v1.5（效果好）
# 英文推荐：sentence-transformers/all-MiniLM-L6-v2（轻量）
LOCAL_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

# OpenAI Embedding（EMBEDDING_PROVIDER="openai" 时生效）
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"

# ============ LLM 配置 ============
# 可选：
#   - "local" : 使用本地大模型（通过 Ollama，免费但需要下载模型）
#   - "openai" : 使用 OpenAI API（效果好，付费）
LLM_PROVIDER = "local"

# Ollama 配置（LLM_PROVIDER="local" 时生效）
# 需要先安装 Ollama: https://ollama.com/
# 然后下载模型: ollama pull qwen2:7b 或 ollama pull qwen2.5:7b
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:3b"      # 轻量快速版（中文 RAG 最佳选择）
# OLLAMA_MODEL = "qwen2.5:7b"    # 更强但更慢
# OLLAMA_MODEL = "deepseek-r1:7b" # 推理模型，适合数学/逻辑

# OpenAI 配置（LLM_PROVIDER="openai" 时生效）
OPENAI_LLM_MODEL = "gpt-4o-mini"  # 性价比最高的选择
# OPENAI_LLM_MODEL = "gpt-4o"     # 效果更好，更贵

# ============ 文档切分配置 ============
CHUNK_SIZE = 1000         # 每个文本块大小（字符数）- 调大以保留完整段落
CHUNK_OVERLAP = 200        # 文本块之间的重叠量（保持上下文连贯）

# ============ 检索配置 ============
RETRIEVAL_K = 6            # 检索时返回的文档块数量 - 调多以获取更全面的信息
# 检索方式：
#   - "similarity" : 相似度搜索（速度最快）
#   - "mmr" : 最大边际相关性（结果更多样化）
#   - "similarity_score_threshold" : 相似度阈值过滤
RETRIEVAL_SEARCH_TYPE = "similarity"

# ============ 系统提示词 ============
SYSTEM_PROMPT = """你是一个知识库问答助手，严格基于提供的文档内容回答。

## 铁律
1. 只基于上面"相关内容"中的文字回答，绝不编造
2. 直接回答，不要任何铺垫、过渡、客套话
3. 不要解释你在做什么，不要分析问题，不要自我纠正
4. 如果相关内容里没有答案，只回复"文档中没有相关信息"，不要补充

## 回答格式
- 总结/复述：直接列出要点，每行一个，不要序号以外的修饰
- 具体问题：直接给答案，附上原文引用
- 多条信息：用 - 分点列出

## 禁止
- ❌ "好的"、"首先"、"值得注意的是"、"总的来说"、"根据文档" 等废话
- ❌ 复述问题
- ❌ 评价文档内容好坏
- ❌ 自己编造文档没有的信息
"""
