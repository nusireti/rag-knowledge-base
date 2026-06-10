# 🚀 接单作品集 & 项目经验

> 以下内容可直接用于：程序员客栈、码市、Upwork、闲鱼、知乎、小红书等平台

---

## 一、一句话简介

```
大三 AI 方向，独立开发企业级 RAG 知识库系统。
提供 AI 应用开发、Python 编程辅导、课设/毕设协助、企业知识库搭建服务。
可本地部署，数据不出网，保护隐私。
```

---

## 二、项目经验（主推 · 企业向）

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
1. **LLM 角色混淆** — 扁平字符串拼接导致模型分不清指令与内容。重构为 SystemMessage/HumanMessage 角色分工，回答质量大幅提升
2. **中文文档加载崩溃** — Unstructured 处理中文 DOCX 时段错误。替换为 python-docx，稳定性提升 10 倍
3. **Agent 调用链过长** — 4 次 LLM 调用优化为 1-2 次，响应时间从 20s+ 降至 3-5s
4. **搜索质量差** — 引入 wttr.in 天气直连 API + 多搜索源降级策略

**项目地址：** https://github.com/nusireti/rag-knowledge-base

---

## 三、服务项目（三档并行）

### 🏢 企业服务

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

---

### 🎓 学生服务（需求量巨大）

#### 服务 3：计算机课设 / 实验辅导
```
接单范围（Python 为主）：
  ✅ 数据分析 + 可视化（Pandas / Matplotlib / PyEcharts）
  ✅ 机器学习 / 深度学习模型（Sklearn / PyTorch / TensorFlow）
  ✅ 爬虫开发（Requests / Scrapy / Selenium）
  ✅ Web 后端（Flask / FastAPI / Django）
  ✅ 算法题 / 数据结构
  ✅ 数据库设计（SQLite / MySQL / PostgreSQL）
  ✅ AI / 大模型相关作业

报价：
  🟢 代码调试 / Bug 修复：50~200 元/次
  🟡 课设完整实现：200~800 元/个
  🔴 毕设辅助：500~2000 元/个
  🟣 期末突击辅导：100~300 元/小时

优势：
  - 同为计算机专业，懂课程要求
  - 代码规范 + 注释完整
  - 包讲解，不只是给代码
  - 紧急单可加急（24h内交付）
```

#### 服务 4：AI 工具 / 脚本定制
```
  ✅ 批量文件处理工具
  ✅ 数据清洗 + 格式转换
  ✅ 自动化脚本（办公自动化）
  ✅ 简单 Web 应用
  ✅ 毕业设计原型开发

报价：200~2000 元/单
```

#### 服务 5：课程报告 / 实验报告排版
```
  ✅ Markdown / LaTeX 排版
  ✅ 实验报告模板定制
  ✅ 数据可视化出图

报价：30~100 元/份
```

---

## 四、技术能力清单

```
┌────────────────────────────────────────────┐
│          技术能力清单                       │
├────────────────────────────────────────────┤
│ 编程语言                                   │
│   Python ⭐⭐⭐⭐⭐ · JavaScript ⭐⭐⭐       │
│   SQL ⭐⭐⭐⭐ · HTML/CSS ⭐⭐⭐             │
├────────────────────────────────────────────┤
│ AI / 大模型 ⭐⭐⭐⭐                        │
│   LangChain · RAG · Agent · Prompt 工程    │
│   Ollama · OpenAI API · 模型部署           │
│   ChromaDB · FAISS · Embedding             │
├────────────────────────────────────────────┤
│ Python 生态 ⭐⭐⭐⭐⭐                      │
│   Pandas/NumPy · Matplotlib · Scikit-learn │
│   PyTorch · Flask/FastAPI · 爬虫           │
├────────────────────────────────────────────┤
│ 后端开发 ⭐⭐⭐⭐                           │
│   FastAPI · SQLAlchemy · RESTful API       │
│   认证系统 · Docker 部署                   │
├────────────────────────────────────────────┤
│ 文档处理 ⭐⭐⭐⭐                           │
│   PyMuPDF · python-docx · OCR 基础         │
│   文本分块 · 语义切分                      │
├────────────────────────────────────────────┤
│ 工具                                       │
│   Git · Docker · Linux · GitHub Actions    │
└────────────────────────────────────────────┘
```

---

## 五、平台自我介绍模板

### 闲鱼（学生向）

```
【计算机专业辅导 | Python | AI | 课设毕设】
📌 大三 AI 方向，独立开发企业级 RAG 知识库系统

可接：
✅ Python 课设 / 实验 / 作业
✅ 数据分析 / 爬虫 / 机器学习
✅ AI / 大模型相关项目
✅ Web 后端（Flask / FastAPI）
✅ 代码调试 + Bug 修复

💰 价格：
  调试 50 起 · 课设 200 起 · 毕设 500 起

🎁 送：代码讲解 + 注释 + 使用说明

💬 私信发需求，免费评估报价
```

### 程序员客栈 / 码市（综合向）

```
【个人简介】
计算机专业大三学生，AI 方向。
独立开发了企业级 RAG 知识库系统（GitHub 开源）。
熟悉 Python 全栈、AI 应用开发。

【可接项目】
🏢 企业级：知识库搭建（2000 起）、AI 问答系统定制（3000 起）
🎓 学生类：课设辅导（200 起）、毕设辅助（500 起）
🔧 工具类：Python 脚本（200 起）、爬虫（300 起）

【技术优势】
1. 全栈能力：从模型部署到前端界面，一条龙交付
2. 学生价格：市场价 30%~50%，质量不打折
3. 响应快：一般 2h 内回复，急单可加急

私信详聊，免费需求评估。
```

### Upwork（英文 · 国际）

```
**AI Developer & Python Freelancer**

Computer Science student specializing in AI application development.
Built a production-grade RAG knowledge base system (open source on GitHub).

**What I can do:**
- Build private AI knowledge base systems for companies
- Python development (data analysis, web scraping, automation)
- Machine Learning / Deep Learning projects
- College CS assignment tutoring (code review, debugging, implementation)

**Tech Stack:**
Python, LangChain, RAG, ChromaDB, Ollama, Streamlit, Docker
Pandas, NumPy, Scikit-learn, PyTorch, FastAPI

**Why me:**
- Full ownership: backend to UI, I handle everything
- Affordable rates, professional quality
- Fast turnaround, clear communication

Contact me for a free consultation!
```

---

## 六、报价总表

| 服务 | 起步价 | 交付周期 | 客户群 |
|------|--------|---------|--------|
| 企业知识库搭建 | 2,000 元 | 3~5 天 | 🏢 企业 |
| 知识库定制开发 | 5,000 元 | 1~2 周 | 🏢 企业 |
| 企业级部署 | 8,000 元 | 2~3 周 | 🏢 企业 |
| Python 课设/实验 | 200 元 | 1~3 天 | 🎓 学生 |
| 毕设辅助 | 500 元 | 3~7 天 | 🎓 学生 |
| 代码调试/Bug修复 | 50 元 | 1~2 小时 | 🎓 学生 |
| Python 工具开发 | 200 元 | 1~3 天 | 通用 |
| 爬虫开发 | 300 元 | 1~3 天 | 通用 |
| AI 自动化工作流 | 2,000 元 | 3~7 天 | 🏢 企业 |
| 考试突击辅导 | 100 元/小时 | 即时 | 🎓 学生 |

---

## 七、获客渠道

| 平台 | 发什么 | 频率 |
|------|--------|------|
| **闲鱼** | 挂商品「课设辅导」「知识库搭建」 | 每天擦亮 |
| **知乎** | 发技术文章 + 项目经验 | 每周 1 篇 |
| **小红书** | 发截图 + 成果展示 | 每周 2~3 篇 |
| **程序员客栈** | 完善简历 + 投项目 | 每周投 5 个 |
| **QQ/微信群** | 计算机专业群、接单群 | 每天冒泡 |
| **B站** | 录屏教程 + 项目展示 | 每两周 1 个 |

---

## 八、作品集截图建议

在平台上展示以下截图更有说服力：

1. **GitHub 项目首页** — 证明是真实项目
2. **登录页面** — 展示用户系统
3. **问答界面（带来源引用）** — 展示核心功能
4. **Agent 模式（联网搜索）** — 展示技术深度
5. **代码结构截图** — 展示工程能力

---

> 📌 最后更新：2026 年 6 月
> 由项目开发者本人编写，真实可查
> GitHub: https://github.com/nusireti/rag-knowledge-base
