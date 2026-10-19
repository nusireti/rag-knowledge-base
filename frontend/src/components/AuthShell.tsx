import type { ReactNode } from 'react';

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="auth-shell">
      <section className="auth-brand">
        <div>
          <div className="auth-kicker">RAG KNOWLEDGE BASE · 2027</div>
          <h1>
            把文档
            <br />
            变成会回答的
            <br />
            知识库。
          </h1>
          <p className="auth-lede">
            语义 + 关键词混合检索，Agent 自主选择工具，多模型可切换。
            从上传、索引到流式问答，一条完整链路。
          </p>
        </div>

        <div className="auth-points">
          <div className="auth-point">
            <b>混合检索</b>
            <span>向量语义 + BM25 关键词，召回更稳</span>
          </div>
          <div className="auth-point">
            <b>Agent 工具调用</b>
            <span>知识库 / 联网 / 计算，自主决定</span>
          </div>
          <div className="auth-point">
            <b>可验证的工程</b>
            <span>68 项测试 · 多租户隔离 · 安全加固</span>
          </div>
        </div>

        <div className="auth-foot">
          nusireti · 大连海洋大学 · AI 应用开发
        </div>
      </section>

      <section className="auth-form-side">
        <div className="auth-card">
          <h2>{title}</h2>
          <p className="sub">{subtitle}</p>
          {children}
          {footer ? <div className="auth-switch">{footer}</div> : null}
        </div>
      </section>
    </div>
  );
}
