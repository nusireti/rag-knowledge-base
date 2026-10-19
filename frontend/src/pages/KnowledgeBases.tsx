import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  BookOpen,
  Eye,
  FileText,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
  X,
} from 'lucide-react';
import {
  docs as docsApi,
  getErrorMessage,
  kb as kbApi,
  type DocumentInfo,
  type KnowledgeBase,
} from '../api';
import {
  Button,
  Empty,
  Modal,
  PageHeader,
  Skeleton,
  Spinner,
  Stat,
  useToast,
} from '../components/ui';

type ConfirmState =
  | { kind: 'kb'; kb: KnowledgeBase }
  | { kind: 'doc'; doc: DocumentInfo }
  | null;

export function KnowledgeBasesPage() {
  const navigate = useNavigate();
  const toast = useToast();

  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);

  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDisplay, setNewDisplay] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const [confirm, setConfirm] = useState<ConfirmState>(null);
  const [confirming, setConfirming] = useState(false);

  const [selected, setSelected] = useState<KnowledgeBase | null>(null);
  const [docs, setDocs] = useState<DocumentInfo[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);

  const [preview, setPreview] = useState<{ name: string; content: string } | null>(
    null,
  );
  const [previewLoading, setPreviewLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadKbs = async () => {
    try {
      const res = await kbApi.list();
      setKbs(res.data || []);
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadKbs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadDocs = async (kbName: string) => {
    setDocsLoading(true);
    try {
      const res = await docsApi.list(kbName);
      setDocs(res.data || []);
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setDocsLoading(false);
    }
  };

  const openKb = (item: KnowledgeBase) => {
    setSelected(item);
    void loadDocs(item.name);
  };

  const closeKb = () => {
    setSelected(null);
    setDocs([]);
  };

  const handleCreate = async () => {
    if (!/^[a-zA-Z0-9_-]+$/.test(newName.trim())) {
      toast.push('标识符只能包含英文、数字、下划线和短横线', 'error');
      return;
    }
    setCreating(true);
    try {
      await kbApi.create(
        newName.trim(),
        newDisplay.trim() || newName.trim(),
        newDesc.trim(),
      );
      toast.push('知识库已创建', 'success');
      setCreateOpen(false);
      setNewName('');
      setNewDisplay('');
      setNewDesc('');
      await loadKbs();
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleConfirm = async () => {
    if (!confirm) return;
    setConfirming(true);
    try {
      if (confirm.kind === 'kb') {
        await kbApi.delete(confirm.kb.name);
        if (selected?.name === confirm.kb.name) closeKb();
        toast.push('知识库已删除', 'success');
        await loadKbs();
      } else if (selected) {
        await docsApi.delete(selected.name, confirm.doc.name);
        toast.push('文档已删除', 'success');
        await loadDocs(selected.name);
        await loadKbs();
      }
      setConfirm(null);
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setConfirming(false);
    }
  };

  const handleFiles = async (files: FileList | File[]) => {
    if (!selected) return;
    const list = Array.from(files);
    if (list.length === 0) return;

    setUploading(true);
    for (const file of list) {
      try {
        const res = await docsApi.upload(selected.name, file);
        toast.push(
          `${file.name} 已上传${res.indexed ? ` · 索引 ${res.indexed} 个片段` : ''}`,
          'success',
        );
      } catch (err) {
        toast.push(`${file.name}：${getErrorMessage(err)}`, 'error');
      }
    }
    setUploading(false);
    await loadDocs(selected.name);
    await loadKbs();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) void handleFiles(e.dataTransfer.files);
  };

  const handleRebuild = async () => {
    if (!selected) return;
    setRebuilding(true);
    try {
      const res = await docsApi.rebuild(selected.name);
      toast.push(`索引重建完成，共 ${res.chunks} 个片段`, 'success');
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
    } finally {
      setRebuilding(false);
    }
  };

  const openPreview = async (doc: DocumentInfo) => {
    if (!selected) return;
    setPreview({ name: doc.name, content: '' });
    setPreviewLoading(true);
    try {
      const res = await docsApi.preview(selected.name, doc.name, 5000);
      setPreview({ name: doc.name, content: res.content });
    } catch (err) {
      toast.push(getErrorMessage(err), 'error');
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  };

  const totalDocs = kbs.reduce((sum, item) => sum + (item.doc_count || 0), 0);
  const indexedKbs = kbs.filter((item) => (item.doc_count || 0) > 0).length;

  return (
    <>
      <PageHeader
        kicker="KNOWLEDGE BASE / 知识库"
        title="知识库"
        subtitle="把散落的文档收进一个库，混合检索后再交给模型回答。上传即建索引。"
        right={
          <Button variant="primary" onClick={() => setCreateOpen(true)}>
            <Plus size={14} /> 新建知识库
          </Button>
        }
      />

      <div className="stat-grid">
        <Stat value={kbs.length} label="知识库总数" />
        <Stat value={totalDocs} label="文档总数" />
        <Stat value={indexedKbs} label="已建立索引" />
        <Stat value="语义 + 关键词" label="检索模式" />
      </div>

      {loading ? (
        <div className="kb-grid">
          {[0, 1, 2].map((i) => (
            <div className="kb-card" key={i}>
              <Skeleton height={22} width="60%" />
              <div style={{ height: 10 }} />
              <Skeleton height={14} />
              <div style={{ height: 6 }} />
              <Skeleton height={14} width="80%" />
            </div>
          ))}
        </div>
      ) : kbs.length === 0 ? (
        <Empty
          icon={<BookOpen size={22} />}
          title="还没有知识库"
          desc="建一个库，上传几份文档，就能开始基于你自己的资料问答。"
          action={
            <Button variant="primary" onClick={() => setCreateOpen(true)}>
              <Plus size={14} /> 新建知识库
            </Button>
          }
        />
      ) : (
        <div className="kb-grid">
          {kbs.map((item) => (
            <article
              className="kb-card"
              key={item.name}
              onClick={() => openKb(item)}
            >
              <button
                className="kb-del"
                aria-label="删除知识库"
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirm({ kind: 'kb', kb: item });
                }}
              >
                <Trash2 size={14} />
              </button>
              <h3>{item.display_name || item.name}</h3>
              <div className="desc">{item.description || '暂无描述'}</div>
              <div className="slug">{item.name}</div>
              <div className="kb-meta">
                <span>{item.doc_count || 0} 个文档</span>
                <span style={{ color: 'var(--teal)', fontWeight: 500 }}>
                  管理 →
                </span>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* ---------------- 新建知识库 ---------------- */}
      <Modal
        open={createOpen}
        title="新建知识库"
        subtitle="标识符用于目录名与 API 路径，创建后不可修改。"
        onClose={() => setCreateOpen(false)}
        footer={
          <>
            <Button onClick={() => setCreateOpen(false)}>取消</Button>
            <Button
              variant="primary"
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
            >
              {creating ? (
                <>
                  <Spinner size={13} /> 创建中
                </>
              ) : (
                '创建'
              )}
            </Button>
          </>
        }
      >
        <div className="field">
          <label className="label" htmlFor="kb-name">
            标识符
          </label>
          <input
            id="kb-name"
            className="input"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="例如 my-notes"
          />
          <div className="hint">只能包含英文、数字、下划线和短横线。</div>
        </div>
        <div className="field">
          <label className="label" htmlFor="kb-display">
            显示名称
          </label>
          <input
            id="kb-display"
            className="input"
            value={newDisplay}
            onChange={(e) => setNewDisplay(e.target.value)}
            placeholder="可选，默认与标识符相同"
          />
        </div>
        <div className="field" style={{ marginBottom: 0 }}>
          <label className="label" htmlFor="kb-desc">
            描述
          </label>
          <textarea
            id="kb-desc"
            className="textarea"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
            placeholder="这个库用来放什么资料？"
            rows={3}
          />
        </div>
      </Modal>

      {/* ---------------- 删除确认 ---------------- */}
      <Modal
        open={confirm !== null}
        title={
          confirm?.kind === 'kb'
            ? '删除知识库？'
            : '删除这份文档？'
        }
        onClose={() => setConfirm(null)}
        footer={
          <>
            <Button onClick={() => setConfirm(null)}>取消</Button>
            <Button
              variant="danger"
              onClick={handleConfirm}
              disabled={confirming}
            >
              {confirming ? (
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
          {confirm?.kind === 'kb' ? (
            <>
              将删除知识库 <b>{confirm.kb.display_name || confirm.kb.name}</b>{' '}
              及其中的全部文档与索引，<b>不可恢复</b>。
            </>
          ) : (
            <>
              将删除文档 <b>{confirm?.doc.name}</b> 及其向量片段，然后自动重建索引。
            </>
          )}
        </p>
      </Modal>

      {/* ---------------- 知识库详情抽屉 ---------------- */}
      {selected ? (
        <>
          <div className="drawer-backdrop" onClick={closeKb} />
          <aside className="drawer">
            <button className="drawer-close" onClick={closeKb} aria-label="关闭">
              <X size={18} />
            </button>
            <div className="drawer-head">
              <div className="kicker">KNOWLEDGE BASE</div>
              <h2>{selected.display_name || selected.name}</h2>
              <div
                style={{
                  fontSize: 11.5,
                  color: 'var(--ink-mute)',
                  marginTop: 4,
                }}
              >
                {selected.name} · {docs.length} 个文档
              </div>
            </div>

            <div className="drawer-body">
              <div
                className={`dropzone ${dragOver ? 'drag' : ''}`}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                <div className="dz-icon">
                  {uploading ? <Spinner size={22} /> : <UploadCloud size={22} />}
                </div>
                <div className="dz-title">
                  {uploading ? '正在上传并建立索引…' : '拖拽文件到这里，或点击选择'}
                </div>
                <div className="dz-hint">
                  支持 PDF / DOCX / TXT / MD，可多选；上传后自动切块入库
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files?.length) void handleFiles(e.target.files);
                  e.target.value = '';
                }}
              />

              <div className="section-label">
                <span>
                  文档 <span className="count">/ {docs.length}</span>
                </span>
                <Button
                  size="sm"
                  onClick={handleRebuild}
                  disabled={rebuilding || docs.length === 0}
                >
                  {rebuilding ? (
                    <>
                      <Spinner size={12} /> 重建中
                    </>
                  ) : (
                    <>
                      <RefreshCw size={12} /> 重建索引
                    </>
                  )}
                </Button>
              </div>

              {docsLoading ? (
                <div>
                  {[0, 1, 2].map((i) => (
                    <div key={i} style={{ padding: '10px 0' }}>
                      <Skeleton height={18} />
                    </div>
                  ))}
                </div>
              ) : docs.length === 0 ? (
                <div className="note">
                  还没有文档。先上传一份 PDF 或 Markdown，再回到问答页提问。
                </div>
              ) : (
                <div className="doc-list">
                  {docs.map((doc) => (
                    <div className="doc-row" key={doc.name}>
                      <FileText size={15} className="doc-icon" />
                      <div className="doc-name" title={doc.name}>
                        {doc.name}
                      </div>
                      <div className="doc-size">{doc.size_str || ''}</div>
                      <div className="doc-actions">
                        <button
                          title="预览"
                          onClick={() => void openPreview(doc)}
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          title="删除"
                          className="danger"
                          onClick={() => setConfirm({ kind: 'doc', doc })}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="note" style={{ marginTop: 20 }}>
                上传后会自动切片并写入向量库。如果问答时提示「文档中没有相关信息」，
                多半是索引没建好，点右上角「重建索引」即可。
              </div>

              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  marginTop: 18,
                  flexWrap: 'wrap',
                }}
              >
                <Button
                  variant="dark"
                  onClick={() => {
                    closeKb();
                    navigate(`/app/chat?kb=${encodeURIComponent(selected.name)}`);
                  }}
                >
                  用这个库开始问答 <ArrowUpRight size={14} />
                </Button>
              </div>
            </div>
          </aside>
        </>
      ) : null}

      {/* ---------------- 文档预览 ---------------- */}
      <Modal
        open={preview !== null}
        title={preview?.name || '文档预览'}
        subtitle="仅显示文档前 5000 个字符"
        onClose={() => setPreview(null)}
        wide
        footer={<Button onClick={() => setPreview(null)}>关闭</Button>}
      >
        {previewLoading ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              color: 'var(--ink-mute)',
              fontSize: 13,
              padding: '30px 0',
            }}
          >
            <Spinner size={15} /> 正在读取文档…
          </div>
        ) : (
          <div className="preview-body">
            {preview?.content || '（空文档）'}
          </div>
        )}
      </Modal>
    </>
  );
}
