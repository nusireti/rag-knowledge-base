# 🚀 接单作品集 & 项目经验

> 以下内容可直接用于：程序员客栈、码市、Upwork、闲鱼、知乎等平台的个人介绍

---

## 一、一句话简介

```
大三 AI 方向，独立开发企业级 RAG 知识库系统。
提供私有知识库搭建、AI 问答系统定制、文档智能化服务。
可本地部署，数据不出网，保护企业隐私。
```

---

## 二、项目经验（直接复制用）

---

### 📌 项目名称：RAG 智能知识库系统

**技术栈：** Python · LangChain · ChromaDB · Ollama · Streamlit · SQLAlchemy · Docker

**项目简介：**
独立开发的企业级 RAG（检索增强生成）知识库问答系统。支持多用户、多知识库、Agent 工具调用、联网搜索。用户上传 PDF/Word/Markdown 文档后，AI 能基于文档内容进行智能问答。系统完全本地化部署，数据不出企业内网。

**核心功能：**
- 🔐 多用户认证 + 数据隔离（bcrypt + Session Token）
- 📚 多知识库管理（创建/切换/删除）
- 📄 多格式文档支持（PDF/TXT/MD/DOCX）
- 🧠 RAG 精准问答（基于文档内容的可溯源回答）
- 🤖 Agent 模式（AI 自动选择：知识库检索/联网搜索/计算器）
- ⚡ 流式输出（文字逐字显示，无需等待完整生成）
- 💬 多轮对话（AI 记忆上下文，连续提问）
- 🐳 Docker 一键部署（含 Ollama 模型服务）
- 🗄️ SQLAlchemy 数据库持久化
- 🚀 GPU 自动加速（NVIDIA CUDA）

**技术难点与解决方案：**
1. **LLM 角色混淆问题** — 初始版本使用扁平字符串拼接，模型分不清系统指令与用户内容。重构为 SystemMessage/HumanMessage 角色分工，回答质量大幅提升。
2. **中文文档加载崩溃** — UnstructuredWordLoader 处理中文 DOCX 时段错误。替换为 python-docx 自定义加载器，加载稳定性提升 10 倍。
3. **Agent 调用链过长** — 每次问答 4 次 LLM 调用导致响应 20s+。优化为 1-2 次调用，响应时间缩短至 3-5s。
4. **搜索质量差** — DuckDuckGo 中文搜索不准。引入 wttr.in 天气直连 API + 多搜索源降级策略。

**项目地址：** https://github.com/[你的用户名]/rag-knowledge-base

---

### 📌 可提供的服务

#### 服务 1：企业私有知识库搭建
```
为企业搭建内部知识库系统，支持上传公司文档/制度/手册，
员工可自然语言提问，AI 基于内部文档回答。

报价：2000~8000 元/套
交付内容：
  ✅ 私有化部署（服务器或本地）
  ✅ 多部门/多知识库支持
  ✅ 用户权限管理
  ✅ 1 个月技术支持
  ✅ 部署文档 + 使用手册
```

#### 服务 2：知识库定制开发
```
在基础版上增加定制功能：
  ✅ 接入企业微信/飞书/钉钉机器人
  ✅ LDAP/OAuth 企业统一登录
  ✅ 自定义文档处理流程
  ✅ 品牌定制 UI
  ✅ API 接口对接

报价：5000~15000 元/套
```

#### 服务 3：AI 工具开发
```
  ✅ 批量文档处理工具
  ✅ AI 自动化工作流
  ✅ 数据清洗 + 分析
  ✅ Python 爬虫 + 数据处理

报价：500~5000 元/单
```

---

## 三、技术能力清单

```
┌────────────────────────────────────────────┐
│          技术能力清单                       │
├────────────────────────────────────────────┤
│ 编程语言                                   │
│   Python · JavaScript · SQL                │
├────────────────────────────────────────────┤
│ AI / 大模型                                │
│   LangChain · RAG · Agent · Function Call  │
│   Ollama · OpenAI API · 文心/通义/DEEPSEEK │
│   Prompt Engineering · 向量数据库           │
│   ChromaDB · FAISS · Embedding 模型        │
├────────────────────────────────────────────┤
│ 后端开发                                   │
│   FastAPI · SQLAlchemy · SQLite/PostgreSQL │
│   RESTful API · JWT/bcrypt 认证 · Docker   │
├────────────────────────────────────────────┤
│ 前端开发                                   │
│   Streamlit · Gradio · 响应式 UI 设计      │
├────────────────────────────────────────────┤
│ 文档处理                                   │
│   PyMuPDF · python-docx · Unstructured     │
│   文本分块 · 语义切分 · OCR               │
├────────────────────────────────────────────┤
│ 工具                                       │
│   Git · Docker · Linux · CI/CD 基础        │
│   结构化日志 · 异常处理 · 性能优化         │
└────────────────────────────────────────────┘
```

---

## 四、平台自我介绍模板

### 程序员客栈 / 码市 个人简介

```
【个人简介】
计算机专业大三学生，AI 方向。独立开发了企业级 RAG 知识库系统，
熟悉 LangChain、大模型应用开发、文档智能化处理。

【技术优势】
1. AI 应用全栈能力：从模型部署到前端界面，一条龙交付
2. 本地化部署：所有方案支持私有化，数据不出企业内网
3. 学生价格：价格仅为市场价 30%~50%，质量不打折

【可接项目】
- 企业知识库搭建（2000 起）
- AI 文档问答系统定制（3000 起）
- 爬虫/数据处理（500 起）
- Python 工具开发（500 起）

【联系方式】
私信详聊，免费需求评估。
```

### Upwork 英文简介

```
**AI Developer & RAG Specialist**

I'm a computer science student specializing in AI, with hands-on experience 
building production-grade RAG (Retrieval-Augmented Generation) systems.

**What I can do for you:**
- Build private knowledge base systems for your company
- Develop AI-powered document Q&A applications
- Customize RAG pipelines with local or cloud LLMs
- Deploy AI applications with Docker

**Technical Skills:**
Python, LangChain, ChromaDB, Ollama, Streamlit, SQLAlchemy, Docker

**Why work with me:**
- Full ownership: I handle everything from backend to UI
- Privacy-first: All solutions support on-premise deployment
- Affordable rates with professional quality

Contact me for a free consultation!
```

---

## 五、报价参考

| 服务 | 起步价 | 交付周期 | 难度 |
|------|--------|---------|------|
| 基础知识库搭建 | 2,000 元 | 3~5 天 | ⭐⭐ |
| 定制化知识库 | 5,000 元 | 1~2 周 | ⭐⭐⭐ |
| 企业级部署 | 8,000 元 | 2~3 周 | ⭐⭐⭐⭐ |
| API 对接/集成 | 3,000 元 | 1 周 | ⭐⭐⭐ |
| Python 工具开发 | 500 元 | 1~3 天 | ⭐ |
| AI 自动化工作流 | 2,000 元 | 3~7 天 | ⭐⭐⭐ |

---

## 六、作品集截图建议

建议在平台上展示以下截图：

1. **登录页面** — 展示用户系统
2. **知识库列表** — 展示多知识库管理
3. **问答界面** — 展示流式输出 + 来源引用
4. **Agent 模式** — 展示联网搜索/计算器功能
5. **Docker 部署** — 展示专业部署能力
6. **技术架构图** — 展示系统设计能力

---

> 📌 最后更新：2026 年 6 月
> 由项目开发者本人编写，真实可查
