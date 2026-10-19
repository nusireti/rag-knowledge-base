import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  BookOpen,
  Download,
  MessageSquareText,
  Plus,
  Send,
  Sparkles,
  Trash2,
} from 'lucide-react';
import {
  chat as chatApi,
  getErrorMessage,
  kb as kbApi,
  streamAsk,
  type ChatMessage,
  type Conversation,
  type KnowledgeBase,
} from '../api';
import { readSSE } from '../lib/sse';
import {
  Button,
  Modal,
  Spinner,
  useToast,
} from '../components/ui';

interface Source {
  source?: string;
  content?: string;
}

interface UIMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  mode?: string;
  error?: string;
  streaming?: boolean;
}

let msgSeq = 0;
const uid = () => `m${++msgSeq}`;

const SUGGESTIONS = [
  {
    title: '总结核心内容',
    text: '把上传的资料总结成 5 条要点，每条一句话。',
  },
  {
    title: '提取关键数据',
    text: '文档里提到了哪些关键数字或指标？请列出并注明出处。',
  },
  {
    title: '对比差异',
    text: '这几份文档之间有哪些说法不一致的地方？',
  },
  {
    title: '追问细节',
    text: '针对文档里的方案，列出它的前提假设和潜在风险。',
  },
];

export function ChatPage() {
  const [searchParams] = useSearchParams();
  const toast = useToast();

  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [kbName, setKbName] = useState(searchParams.get('kb') || '');
  const [mode, setMode] = useState<'rag' | 'agent'>('rag');
  const [hybrid, setHybrid] = useState(true);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [convId, setConvId] = useState('');
  const [loadingConv, setLoadingConv] = useState(false);
  const [convToDelete, setConvToDelete] = useState<Conversation | null>(null);
  const [deletingConv, setDeletingConv] = useState(false);

  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* ---------------- 初始化 ---------------- */
  useEffect(() => {
    kbApi
      .list()
      .then((res) => {
        const list = res.data || [];
        setKbs(list);
        setKbName((prev) => prev || list[0]?.name || '');
      })
      .catch((err) => toast.push(getErrorMessage(err), 'error'));
    void refreshConversations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const refreshConversations = async () => {
    try {
      const res = await chatApi.listConversations();
      setConversations(res.data || []);
    } catch {
      /* 列表加载失败不打断主流程 */
    }
  };

  /* ---------------- 对话操作 ---------------- */
  const newConversation = () => {
    setConvId('');
    setMessages([]);
    setInput('');
    requestAnimationFrame(() => textareaRef.current?.focus());
  };

  const loadConversation = async (id: string) => {
    setLoadingConv(true);
    try {
      const res = await chatApi.getConversation(id);
      const mapped: UIMessage[] = (res.data.messages || []).map(
        (m: ChatMessage) => ({
          id: uid(),
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content,
        }),
      );
      setMessages(mapped);
      setConvId(id);
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setLoadingConv(false);
    }
  };

  const deleteConversation = async () => {
    if (!convToDelete) return;
    setDeletingConv(true);
    try {
      await chatApi.deleteConversation(convToDelete.id);
      if (convToDelete.id === convId) newConversation();
      setConvToDelete(null);
      toast.push('对话已删除', 'success');
      await refreshConversations();
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setDeletingConv(false);
    }
  };

  const exportConversation = async () => {
    if (!convId) {
      toast.push('当前还没有可导出的对话', 'error');
      return;
    }
    try {
      const res = await chatApi.exportConversation(convId, 'md');
      const blob = new Blob([res.content], {
        type: 'text/markdown;charset=utf-8',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversation-${convId}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    }
  };

  /* ---------------- 发送 ---------------- */
  const send = async (preset?: string) => {
    const question = (preset ?? input).trim();
    if (!question || sending) return;
    if (mode === 'rag' && !kbName) {
      toast.push('先选一个知识库，或切到 Agent 模式', 'error');
      return;
    }

    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';

    const userMsg: UIMessage = { id: uid(), role: 'user', content: question };
    const aiId = uid();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: aiId, role: 'assistant', content: '', streaming: true },
    ]);
    setSending(true);

    try {
      let activeConv = convId;
      if (!activeConv) {
        const created = await chatApi.createConversation();
        activeConv = created.conv_id;
        setConvId(activeConv);
      }

      const res = await streamAsk({
        question,
        kb_name: kbName,
        mode,
        conv_id: activeConv,
        hybrid_search: hybrid,
      });

      let answer = '';
      for await (const evt of readSSE(res)) {
        if (evt.event === 'token') {
          answer += evt.data;
          setMessages((prev) =>
            prev.map((m) => (m.id === aiId ? { ...m, content: answer } : m)),
          );
        } else if (evt.event === 'sources') {
          let sources: Source[] = [];
          try {
            const parsed = JSON.parse(evt.data);
            if (Array.isArray(parsed)) sources = parsed as Source[];
          } catch {
            /* 来源解析失败不影响回答 */
          }
          setMessages((prev) =>
            prev.map((m) => (m.id === aiId ? { ...m, sources } : m)),
          );
        } else if (evt.event === 'mode') {
          setMessages((prev) =>
            prev.map((m) => (m.id === aiId ? { ...m, mode: evt.data } : m)),
          );
        } else if (evt.event === 'error') {
          throw new Error(evt.data || '生成失败');
        }
      }

      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId
            ? {
                ...m,
                streaming: false,
                content: answer || '（模型没有返回内容）',
              }
            : m,
        ),
      );
      await refreshConversations();
    } catch (err) {
      const msg = getErrorMessage(err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId ? { ...m, streaming: false, error: msg } : m,
        ),
      );
      toast.push(msg, 'error');
    } finally {
      setSending(false);
      requestAnimationFrame(() => textareaRef.current?.focus());
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  const onInput = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.currentTarget;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
  };

  const activeKb = kbs.find((k) => k.name === kbName);

  return (
    <div className="chat-page">
      <div className="chat-main">
        <header className="chat-head">
          <div>
            <div className="chat-title">AI 问答</div>
            <div className="chat-sub">
              混合检索 · 流式输出 · 回答可追溯
            </div>
          </div>

          <div className="chat-head-right">
            <div className="mode-switch">
              <button
                className={mode === 'rag' ? 'active' : ''}
                onClick={() => setMode('rag')}
              >
                RAG
              </button>
              <button
                className={mode === 'agent' ? 'active' : ''}
                onClick={() => setMode('agent')}
              >
                Agent
              </button>
            </div>
            <Button size="sm" onClick={newConversation}>
              <Plus size={13} /> 新对话
            </Button>
          </div>
        </header>

        <div className="chat-scroll" ref={scrollRef}>
          <div className="chat-inner">
            {loadingConv ? (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  color: 'var(--ink-mute)',
                  fontSize: 12.5,
                  padding: '30px 0',
                }}
              >
                <Spinner size={15} /> 正在载入对话…
              </div>
            ) : messages.length === 0 ? (
              <div className="chat-empty">
                <div className="glyph">
                  <MessageSquareText size={24} />
                </div>
                <h2>
                  {activeKb
                    ? `向「${activeKb.display_name || activeKb.name}」提问`
                    : '先从一份文档开始'}
                </h2>
                <p>
                  {mode === 'rag'
                    ? '回答会从你选中的知识库里检索，并附上来源片段。'
                    : 'Agent 模式会自己决定查知识库、联网还是计算，适合开放问题。'}
                </p>
                <div className="suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s.title}
                      className="suggestion"
                      onClick={() => void send(s.text)}
                    >
                      <b>{s.title}</b>
                      {s.text}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`msg ${msg.role === 'user' ? 'user' : ''}`}
                >
                  <div className="msg-inner">
                    <div className="msg-role">
                      {msg.role === 'user' ? 'YOU' : 'ASSISTANT'}
                      {msg.mode ? ` · ${msg.mode.toUpperCase()}` : ''}
                    </div>

                    {msg.error ? (
                      <div className="msg-error">{msg.error}</div>
                    ) : msg.role === 'user' ? (
                      <div className="bubble-user">{msg.content}</div>
                    ) : (
                      <div className="bubble-ai">
                        {msg.content}
                        {msg.streaming ? <span className="cursor" /> : null}
                        {msg.streaming && !msg.content ? (
                          <span className="typing">
                            <i />
                            <i />
                            <i />
                          </span>
                        ) : null}

                        {msg.sources && msg.sources.length > 0 ? (
                          <div className="sources">
                            <div className="sources-head">
                              SOURCES · {msg.sources.length}
                            </div>
                            {msg.sources.map((src, idx) => (
                              <div className="source" key={idx}>
                                <b>{src.source || `片段 ${idx + 1}`}</b>
                                {src.content ? ` — ${src.content}` : ''}
                              </div>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="composer-wrap">
          <div className="composer">
            <div className="composer-box">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={onInput}
                onKeyDown={onKeyDown}
                rows={1}
                placeholder={
                  mode === 'rag' && !kbName
                    ? '先选一个知识库…'
                    : '输入问题，Enter 发送，Shift+Enter 换行'
                }
              />
              <button
                className="composer-send"
                onClick={() => void send()}
                disabled={sending || !input.trim()}
                aria-label="发送"
              >
                {sending ? <Spinner size={16} /> : <Send size={16} />}
              </button>
            </div>
            <div className="composer-foot">
              <div className="kb-pick">
                <BookOpen size={12} />
                <select
                  value={kbName}
                  onChange={(e) => setKbName(e.target.value)}
                >
                  <option value="">不使用知识库（Agent）</option>
                  {kbs.map((k) => (
                    <option key={k.name} value={k.name}>
                      {k.display_name || k.name}
                    </option>
                  ))}
                </select>
              </div>
              <span>
                {sending ? '生成中…' : 'Enter 发送 · Shift+Enter 换行'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ---------------- 右侧上下文 ---------------- */}
      <aside className="chat-aside">
        <div className="aside-head">
          <div className="aside-title">上下文</div>
          <Button size="sm" variant="ghost" onClick={newConversation}>
            <Plus size={13} />
          </Button>
        </div>

        <div className="aside-body">
          <div className="aside-block">
            <div className="aside-label">CONVERSATIONS</div>
            {conversations.length === 0 ? (
              <div style={{ fontSize: 11.5, color: 'var(--ink-mute)' }}>
                还没有对话记录。
              </div>
            ) : (
              conversations.slice(0, 30).map((conv) => (
                <button
                  key={conv.id}
                  className={`conv-item ${conv.id === convId ? 'active' : ''}`}
                  onClick={() => void loadConversation(conv.id)}
                >
                  <span className="conv-title">
                    {conv.title === '新对话'
                      ? `未命名对话 · ${conv.message_count || 0} 条`
                      : conv.title}
                  </span>
                  <span
                    className="conv-del"
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      setConvToDelete(conv);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.stopPropagation();
                        setConvToDelete(conv);
                      }
                    }}
                  >
                    <Trash2 size={12} />
                  </span>
                </button>
              ))
            )}
          </div>

          <div className="aside-block">
            <div className="aside-label">KNOWLEDGE</div>
            <button
              className={`kb-option ${kbName === '' ? 'active' : ''}`}
              onClick={() => setKbName('')}
            >
              <span className="kb-dot" />
              不使用知识库
            </button>
            {kbs.map((k) => (
              <button
                key={k.name}
                className={`kb-option ${kbName === k.name ? 'active' : ''}`}
                onClick={() => setKbName(k.name)}
              >
                <span className="kb-dot" />
                <span
                  style={{
                    flex: 1,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {k.display_name || k.name}
                </span>
                <span style={{ color: 'var(--ink-mute)', fontSize: 10 }}>
                  {k.doc_count || 0}
                </span>
              </button>
            ))}
          </div>

          <div className="aside-block">
            <div className="aside-label">SETTINGS</div>
            <div className="switch-row">
              <span>混合检索</span>
              <button
                className={`switch ${hybrid ? 'on' : ''}`}
                onClick={() => setHybrid((v) => !v)}
                aria-label="切换混合检索"
              />
            </div>
            <div className="switch-row">
              <span>当前模式</span>
              <span className="tag">{mode === 'rag' ? 'RAG' : 'Agent'}</span>
            </div>
            <div className="switch-row">
              <span>知识库</span>
              <span
                style={{
                  maxWidth: 130,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {activeKb ? activeKb.display_name || activeKb.name : '未选择'}
              </span>
            </div>
          </div>

          <div className="aside-block">
            <div className="aside-label">THIS SESSION</div>
            <div className="aside-meta">
              <div className="row">
                <span>消息</span>
                <span>{messages.length} 条</span>
              </div>
              <div className="row">
                <span>对话 ID</span>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 10 }}>
                  {convId || '—'}
                </span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
              <Button size="sm" onClick={exportConversation}>
                <Download size={12} /> 导出
              </Button>
              <Button size="sm" variant="ghost" onClick={newConversation}>
                <Sparkles size={12} /> 清空
              </Button>
            </div>
          </div>

          <div className="aside-block">
            <div className="note" style={{ fontSize: 11 }}>
              回答只基于检索到的片段，模型不会凭空补充。点开来源可对照原文。
            </div>
          </div>
        </div>
      </aside>

      {/* ---------------- 删除对话确认 ---------------- */}
      <Modal
        open={convToDelete !== null}
        title="删除这条对话？"
        onClose={() => setConvToDelete(null)}
        footer={
          <>
            <Button onClick={() => setConvToDelete(null)}>取消</Button>
            <Button
              variant="danger"
              onClick={deleteConversation}
              disabled={deletingConv}
            >
              {deletingConv ? (
                <>
                  <Spinner size={13} /> 删除中
                </>
              ) : (
                '确认删除'
              )}
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13.5, color: 'var(--ink-soft)', lineHeight: 1.9 }}>
          对话记录会被永久删除，<b>不可恢复</b>。
        </p>
      </Modal>

    </div>
  );
}
