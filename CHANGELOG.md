# 📋 开发日志 & 问题记录

> 记录本项目从零到一的完整开发过程，包括所有遇到的问题和解决方案。

---

## [v2.1] - 2026-06-10

### ✨ 新增功能

- **对话历史持久化**：聊天记录自动保存到本地，刷新页面或重启应用后自动恢复
- **导出对话**：支持导出为 Markdown 格式和纯文本格式，可下载保存
- **对话管理**：侧边栏显示全部历史对话，支持切换、删除、新建
- **自动标题**：自动用第一条用户消息作为对话标题

### 🐛 问题 & 修复

#### 问题 11：对话历史在页面刷新后丢失
- **表现**：F5 刷新后所有聊天记录都没了
- **原因**：消息只存在 Streamlit 的 session_state 中（内存），刷新后清空
- **解决方案**：新增 `chat_history.py` 模块，每次对话后将消息序列化为 JSON 存入本地文件
- **启动恢复**：应用启动时自动加载最新的对话
- **代码**：
  ```python
  def save_messages(conv_id, messages):
      with open(f"conversations/{conv_id}.json", "w") as f:
          json.dump({"id": conv_id, "messages": messages, ...}, f)
  ```

---

## [v2.0] - 2026-06-10

### ✨ 新增功能

- **流式输出**：AI 回答逐字显示，不再等待全部生成
- **多轮对话**：AI 能记住对话上下文，连续提问更自然
- **文档管理**：侧边栏可查看已上传的文件列表，支持单独删除
- **暗色主题**：护眼且美观的 UI，毛玻璃效果
- **状态统计**：顶部显示文档段数、文件数、LLM 类型
- **一键重置**：清空向量库从头开始

### 🐛 问题 & 修复

#### 问题 1：页面错误「cannot import name 'create_qa_chain' from 'query'」
- **出现时间**：v2.0 重构后
- **原因**：新版 `query.py` 移除了 `create_qa_chain()` 函数（改用流式接口），但 `app.py` 仍引用它
- **解决方案**：加回 `create_qa_chain()` 函数，同时保持流式接口兼容
- **commit**: `fix: restore create_qa_chain for app.py compatibility`

#### 问题 2：Streamlit 进程反复崩溃
- **原因**：端口 8501 被残留进程占用，新进程绑定失败
- **解决方案**：`kill` 残留进程或用 `taskkill /F /PID` 强制终止，换用 8502 端口
- **预防**：在 `.gitignore` 中忽略 `streamlit.log`

#### 问题 3：输入框文字颜色与背景相近看不清
- **原因**：暗色主题下 CSS 颜色对比度不足
- **解决方案**：重写输入框样式，文字纯白色 + 聚焦紫色光圈 + 占位符半透明
- **修复**：`div[data-testid="stChatInput"] textarea { color: #FFFFFF !important; }`

---

## [v1.1] - 2026-06-10

### 🐛 问题 & 修复

#### 问题 4：每次提问都重新加载 Embedding 模型
- **表现**：每次提问都要等 5~10 秒加载模型
- **原因**：`get_embedding_model()` 每次调用都创建新实例
- **解决方案**：使用模块级全局变量缓存模型实例
- **代码**：
  ```python
  _embedding_model_cache = None
  def get_embedding_model():
      global _embedding_model_cache
      if _embedding_model_cache is not None:
          return _embedding_model_cache
      # ... 加载模型
      _embedding_model_cache = model
      return _embedding_model_cache
  ```
- **效果**：第一次加载后，后续提问秒回

#### 问题 5：文档被重复加载
- **表现**：同一个 .md 文件被加载两次
- **原因**：Windows 文件系统大小写不敏感，`glob("*.MD")` 也匹配了 `.md` 文件
- **解决方案**：用 `set() + resolve()` 对文件绝对路径去重
- **代码**：
  ```python
  seen_paths = set()
  for ext, loader_class in supported_extensions.items():
      for file_path in docs_dir.glob(f"*{ext}"):
          abs_path = str(file_path.resolve())
          if abs_path in seen_paths:
              continue
          seen_paths.add(abs_path)
  ```

#### 问题 6：PyTorch 版本与 Transformers 不兼容
- **表现**：`AttributeError: module 'torch' has no attribute 'float8_e8m0fnu'`
- **原因**：PyTorch 2.6.0 太旧，transformers 5.x 需要更新的特性
- **解决方案**：升级 PyTorch `pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`
- **版本**：torch 2.6.0 → 2.12.0

#### 问题 7：SSL 证书验证失败
- **表现**：`SSL: CERTIFICATE_VERIFY_FAILED` 无法从 HuggingFace 下载模型
- **原因**：国内网络环境对 HuggingFace 访问受限
- **解决方案**：设置镜像源 `export HF_ENDPOINT=https://hf-mirror.com`
- **后续**：下载完成后设置 `local_files_only=True`，不再需要联网

#### 问题 8：langchain 新版 API 变更
- **表现**：`ModuleNotFoundError: No module named 'langchain.chains'`
- **原因**：langchain v0.3+ 移除了旧的 `RetrievalQA` 等链式 API
- **解决方案**：改用 LCEL（LangChain Expression Language）表达式
- **变更**：
  ```python
  # 旧版（已移除）
  from langchain.chains import RetrievalQA
  qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)
  
  # 新版（LCEL）
  chain = (
      {"context": retriever | format_docs, "question": RunnablePassthrough()}
      | prompt | llm | StrOutputParser()
  )
  ```

#### 问题 9：终端 GBK 编码无法显示中文 / emoji
- **表现**：`UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f680'`
- **原因**：Windows 终端默认编码为 GBK，不支持 emoji
- **解决方案**：运行前设置 `export PYTHONIOENCODING=utf-8`

#### 问题 10：langchain-chroma 迁移
- **表现**：`DeprecationWarning: Chroma from langchain_community is deprecated`
- **原因**：langchain-community 中的 Chroma 将在 v1.0 移除
- **解决方案**：改用独立包 `from langchain_chroma import Chroma`

---

## [v1.0] - 2026-06-09

### ✨ 初始功能

- 基础 RAG 流程：文档加载 → 文本切分 → 向量化 → 检索 → 生成
- 支持 PDF / TXT / Markdown / Word 文档
- 本地 Embedding（BAAI/bge-small-zh-v1.5）+ 本地 LLM（Ollama）
- Streamlit Web 界面
- 终端交互模式

### 🐛 初始问题

- Embedding 模型需从 HuggingFace 下载（国内网络需配置镜像）
- 文档切分策略简单，长文档效果一般
- 无缓存，每次启动重新加载
- 页面样式朴素

---

## 📌 已知限制

| 限制 | 说明 | 可能的解决方案 |
|------|------|---------------|
| CPU 推理较慢 | 7B 模型在 CPU 上运行，首次回答约 10~30 秒 | 使用更小的模型（如 qwen2.5:1.5b）或配置 GPU |
| 无用户认证 | 谁都能访问页面 | 加简单的密码认证或 OAuth |
| 单用户 | 不支持多用户隔离 | 每个用户独立 session |
| 无聊天历史持久化 | 刷新页面历史丢失 | 存到 SQLite 或文件中 |
| 不支持图片/表格 | 只处理文档中的文字 | 集成多模态模型或 OCR |

---

## 📊 版本规划

| 版本 | 计划功能 | 状态 |
|------|---------|------|
| v1.0 | 基础 RAG 功能 | ✅ 已完成 |
| v1.1 | 性能优化、Bug 修复 | ✅ 已完成 |
| v2.0 | 流式输出、多轮对话、暗色主题 | ✅ 已完成 |
| v2.1 | 对话历史持久化、导出功能 | ✅ 已完成 |
| v2.2 | 多知识库切换、文档预览 | 🚧 开发中 |
| v3.0 | Agent 工具调用、联网搜索 | 📅 计划中 |
