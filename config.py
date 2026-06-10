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
OLLAMA_MODEL = "deepseek-r1:7b"  # 你已安装的模型
# OLLAMA_MODEL = "qwen2.5:7b"    # 推荐中文模型
# OLLAMA_MODEL = "llama3.1:8b"   # 英文更好，中文一般

# OpenAI 配置（LLM_PROVIDER="openai" 时生效）
OPENAI_LLM_MODEL = "gpt-4o-mini"  # 性价比最高的选择
# OPENAI_LLM_MODEL = "gpt-4o"     # 效果更好，更贵

# ============ 文档切分配置 ============
CHUNK_SIZE = 500          # 每个文本块大小（字符数）
CHUNK_OVERLAP = 100        # 文本块之间的重叠量（保持上下文连贯）

# ============ 检索配置 ============
RETRIEVAL_K = 4            # 检索时返回的文档块数量
# 检索方式：
#   - "similarity" : 相似度搜索（速度最快）
#   - "mmr" : 最大边际相关性（结果更多样化）
#   - "similarity_score_threshold" : 相似度阈值过滤
RETRIEVAL_SEARCH_TYPE = "similarity"

# ============ 系统提示词 ============
SYSTEM_PROMPT = """你是一个知识库问答助手，基于提供的文档内容回答用户的问题。

规则：
1. 只能基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，如实说"文档中没有提到这个问题"
3. 回答要简洁清晰，用中文回复
4. 可以引用文档中的原文
5. 如果问题不明确，可以追问澄清
"""
