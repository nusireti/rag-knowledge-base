# 🧠 RAG 智能知识库

> 基于 LangChain + ChromaDB + Ollama 的本地 RAG 知识库问答系统  
> 支持多轮对话、流式输出、文档管理，**完全本地运行，无需联网，保护数据隐私**

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📸 界面预览

```
┌──────────────────────────────────────────────────────────┐
│  🧠 RAG 智能知识库                                       │
│  上传文档，让 AI 基于你的内容回答问题                     │
├──────────────────────────────────────────────────────────┤
│  📊 文档段数: 11  文件数: 3  LLM: LOCAL  状态: ● 已就绪 │
├──────────────┬───────────────────────────────────────────┤
│  ⚙️ 管理面板  │  💬 用户消息                              │
│              │  🤖 AI 回答 (流式输出)                     │
│  📤 上传文档  │     📄 来源: xxx.pdf                      │
│  [🔄刷新]    │  💬 用户消息                              │
│  [💬清空]    │  🤖 AI 回答 (带对话记忆)                  │
│              │                                           │
│  📂 文档列表  │  ┌──────────────────────────────┐        │
│  xxx.pdf ✕   │  │ 输入你的问题...              │        │
│  xxx.md  ✕   │  └──────────────────────────────┘        │
└──────────────┴───────────────────────────────────────────┘
```

暗色主题 · 聊天气泡 · 来源卡片 · 流式输出 · 多轮对话

---

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🏠 **完全本地运行** | 所有模型在本地运行，数据不出电脑，隐私安全 |
| 📄 **多格式支持** | PDF / TXT / Markdown / Word 文档一键上传 |
| ⚡ **流式输出** | 文字逐个出现，不用等全部生成完 |
| 💬 **多轮对话** | AI 能记住上下文，连续提问 |
| 📂 **文档管理** | 侧边栏查看、删除已上传文件 |
| 🎨 **暗色主题** | 护眼且美观的现代 UI 设计 |
| 🔧 **灵活配置** | 支持本地模型（Ollama）和 OpenAI API |
| 🚀 **高性能** | Embedding 模型全局缓存，第二次提问秒回 |

---

## 🗺 项目背景与开发历程

### 为什么做这个项目？

这是一个计算机专业大三学生的线上兼职实践项目。目标是用 AI 技术做一个能真正帮到人的工具，同时积累项目经验用于接单。

### 开发日志

| 阶段 | 内容 |
|------|------|
| **v1.0** | 基础 RAG 功能：文档上传 → 向量化 → 问答 |
| **v1.1** | 修复性能问题：模型缓存、重复加载、流式输出 |
| **v2.0** | UI 全面升级：暗色主题、文档管理、多轮对话 |

### 🐛 遇到并解决的问题

详见 [CHANGELOG.md](./CHANGELOG.md)，以下是关键问题：

1. **⚠️ Embedding 模型每次提问都重加载** → 全局缓存，首次加载后复用
2. **⚠️ Windows 上文档重复加载** → 大小写不敏感文件系统导致 glob 重复匹配，用 set 去重
3. **⚠️ PyTorch 版本不兼容** → transformers v5 要求 torch≥2.6，升级解决
4. **⚠️ SSL 证书验证失败（国内网络）** → 设置 `HF_ENDPOINT=https://hf-mirror.com`
5. **⚠️ langkain 新版 API 变更** → `RetrievalQA` 移除，改用 LCEL 表达式
6. **⚠️ 终端 GBK 编码问题** → 设置 `PYTHONIOENCODING=utf-8`
7. **⚠️ Streamlit 端口被占用** → kill 残留进程或更换端口
8. **⚠️ 输入框文字看不清** → 优化 CSS 颜色对比度

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- [Ollama](https://ollama.com/)（用于本地 LLM）

### 1️⃣ 克隆项目

```bash
git clone https://github.com/yourusername/rag-knowledge-base.git
cd rag-knowledge-base
```

### 2️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

### 3️⃣ （可选）安装 Ollama + 下载模型

```bash
# 下载安装: https://ollama.com/
ollama pull deepseek-r1:7b   # 或 qwen2.5:7b、llama3.1:8b 等
ollama serve                 # 启动 Ollama 服务
```

### 4️⃣ 放入文档

把你的 PDF / TXT / MD / DOCX 文件放到 `documents/` 目录。

### 5️⃣ 运行

```bash
streamlit run app.py
```

浏览器打开 **http://localhost:8501**，点击「刷新知识库」即可开始提问！

---

## 🎯 使用方式

### Web 界面（推荐）

```bash
streamlit run app.py
```

浏览器访问显示的地址（默认 http://localhost:8501）。

### 终端模式

```bash
python query.py
```

直接在终端中对话。

---

## ⚙️ 配置说明

编辑 `config.py`：

```python
# Embedding 模型：local | openai
EMBEDDING_PROVIDER = "local"

# LLM：local（Ollama）| openai
LLM_PROVIDER = "local"

# Ollama 模型名（LLM_PROVIDER="local" 时生效）
OLLAMA_MODEL = "deepseek-r1:7b"

# 文档切分大小
CHUNK_SIZE = 500

# 每次检索返回的文档块数
RETRIEVAL_K = 4
```

### 切换为 OpenAI

```bash
export OPENAI_API_KEY="sk-xxx"
# config.py 中改为：
# EMBEDDING_PROVIDER = "openai"
# LLM_PROVIDER = "openai"
```

---

## 📁 项目结构

```
rag-knowledge-base/
├── app.py                 # Streamlit Web 界面（带流式输出）
├── query.py               # 问答引擎（检索 + 生成）
├── ingest.py              # 文档导入 + 向量化
├── config.py              # 全局配置文件
├── requirements.txt       # Python 依赖
├── .streamlit/
│   └── config.toml        # Streamlit 主题配置
├── documents/             # 📂 放你的文档文件
│   └── AI入门指南.md       # 示例文档
├── vector_store/          # 🔄 向量数据库（运行后自动生成）
├── CHANGELOG.md           # 开发日志 & 问题记录
├── CONTRIBUTING.md        # 贡献指南
├── LICENSE                # MIT 开源协议
├── setup.bat              # Windows 一键安装脚本
└── README.md
```

---

## 🧠 技术栈

| 组件 | 技术选型 |
|------|---------|
| **框架** | LangChain (LCEL) |
| **向量数据库** | ChromaDB |
| **Embedding** | BAAI/bge-small-zh-v1.5（本地） |
| **大语言模型** | Ollama + deepseek-r1:7b |
| **Web 界面** | Streamlit |
| **文档加载** | PyMuPDF / Unstructured / python-docx |

---

## 📌 接单变现思路

这个项目本身就可以作为你的 **作品集**：

| 方向 | 报价参考 |
|------|---------|
| 帮企业搭建私有知识库 | 2000~8000 元/单 |
| 知识库定制开发（多轮对话、权限管理） | 5000~15000 元/单 |
| 接入微信/飞书/钉钉机器人 | 1000~5000 元/单 |
| 部署到云服务器 | 500~2000 元/单 |

---

## 📄 开源协议

[MIT License](./LICENSE)

---

## 🙏 致谢

- 本项目由 **大三 AI 方向学生** 在学习与实践过程中完成
- 感谢所有开源社区的支持：LangChain、ChromaDB、Streamlit、Ollama、HuggingFace

---

*Made with ❤️ by a Chinese AI student*
