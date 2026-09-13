import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { kb as kbApi } from '../api';

interface KB {
  name: string;
  display_name: string;
  description?: string;
  doc_count?: number;
}

export function KnowledgeBasesPage() {
  const navigate = useNavigate();
  const [kbs, setKbs] = useState<KB[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDisplay, setNewDisplay] = useState('');

  const loadKbs = async () => {
    try {
      const res = await kbApi.list();
      setKbs(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadKbs(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await kbApi.create(newName.trim(), newDisplay.trim() || newName.trim());
      setShowCreate(false);
      setNewName('');
      setNewDisplay('');
      loadKbs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`确定删除知识库 "${name}"？`)) return;
    try {
      await kbApi.delete(name);
      loadKbs();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-[#2D3748]">知识库</h1>
          <p className="text-sm text-[#718096] mt-1">管理你的知识库，上传文档后进行 AI 问答</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-[#6C8CFF] hover:bg-[#5A7AE8] text-white rounded-lg text-sm font-medium transition-all"
        >
          ＋ 新建知识库
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-5 mb-6 space-y-3">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="标识符 (英文/数字/下划线)"
            className="w-full px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF]"
          />
          <input
            type="text"
            value={newDisplay}
            onChange={(e) => setNewDisplay(e.target.value)}
            placeholder="显示名称（可选）"
            className="w-full px-4 py-2 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF]"
          />
          <div className="flex gap-2">
            <button onClick={handleCreate} className="px-4 py-2 bg-[#6C8CFF] text-white rounded-lg text-sm">创建</button>
            <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-[#EDF2F7] rounded-lg text-sm">取消</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center text-[#718096] py-12">加载中...</div>
      ) : kbs.length === 0 ? (
        <div className="text-center text-[#718096] py-12">
          <div className="text-3xl mb-3">📚</div>
          <p>还没有知识库</p>
          <button onClick={() => setShowCreate(true)} className="text-[#6C8CFF] text-sm mt-2 hover:underline">
            创建一个
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {kbs.map((kb) => (
            <div
              key={kb.name}
              className="bg-white rounded-xl border border-[#E2E8F0] p-5 hover:shadow-md transition-all cursor-pointer"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-medium text-[#2D3748]">{kb.display_name || kb.name}</h3>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(kb.name); }}
                  className="text-[#CBD5E0] hover:text-red-500 text-sm"
                >
                  ✕
                </button>
              </div>
              {kb.description && (
                <p className="text-sm text-[#718096] mb-3 line-clamp-2">{kb.description}</p>
              )}
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#A0AEC0]">{kb.doc_count || 0} 个文件</span>
                <button
                  onClick={() => navigate(`/app/chat?kb=${kb.name}`)}
                  className="text-xs text-[#6C8CFF] hover:underline"
                >
                  去问答 →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
