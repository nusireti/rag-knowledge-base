# 🤝 贡献指南

感谢你对本项目的兴趣！以下是一些参与贡献的指引。

## 🐛 报告 Bug

如果你发现了 Bug，请提交 Issue 并包含以下信息：

1. **问题描述**：什么情况？预期行为 vs 实际行为
2. **复现步骤**：怎么操作才会出现这个问题
3. **截图/日志**：错误信息截图或终端输出
4. **环境信息**：
   - 操作系统：
   - Python 版本：
   - 相关包版本（`pip list | grep -E "langchain|streamlit|chroma"`）：

## 💡 功能建议

欢迎提交新功能建议！请在 Issue 中说明：

1. **功能描述**：你想加什么功能？
2. **使用场景**：什么情况下会用到它？
3. **实现思路**（可选）：你觉得怎么实现比较好？

## 🔧 提交 PR

1. Fork 本仓库
2. 创建你的特性分支：`git checkout -b feature/amazing-feature`
3. 提交你的改动：`git commit -m 'feat: add amazing feature'`
4. 推送到分支：`git push origin feature/amazing-feature`
5. 提交 Pull Request

### Commit 规范

参考 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新功能
fix: Bug 修复
docs: 文档更新
style: 代码格式（不影响功能）
refactor: 代码重构
perf: 性能优化
test: 测试相关
chore: 构建过程或辅助工具变动
```

示例：
```
feat: 添加流式输出支持
fix: 修复 Windows 上文档重复加载的问题
docs: 更新 README 使用说明
```

## 🧪 本地开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 安装 pre-commit hooks（可选）
pip install pre-commit
pre-commit install
```

## 📁 代码结构说明

```
rag-knowledge-base/
├── app.py          # Web 界面（Streamlit）
├── query.py        # 问答引擎
├── ingest.py       # 文档导入
├── config.py       # 配置文件
└── documents/      # 文档目录
```

---

再次感谢你的贡献！🎉
