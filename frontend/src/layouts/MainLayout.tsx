import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { auth as authApi, kb as kbApi } from '../api';

const NAV_ITEMS = [
  { path: '/app/knowledge-bases', label: '知识库', icon: '📚' },
  { path: '/app/chat', label: 'AI 问答', icon: '💬' },
];

export function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState(localStorage.getItem('username') || '用户');
  const [showRightPanel, setShowRightPanel] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }
  }, [navigate]);

  // Show right panel on chat page
  useEffect(() => {
    setShowRightPanel(location.pathname === '/app/chat');
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
  };

  return (
    <div className="h-screen flex flex-col bg-[#F5F7FA]">
      {/* 顶部导航 */}
      <header className="h-[56px] bg-white border-b border-[#E2E8F0] flex items-center px-5 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-lg">🦝</span>
          <span className="font-semibold text-[#2D3748]">RAG 知识库</span>
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-4">
          <span className="text-sm text-[#718096]">{username}</span>
          <button
            onClick={handleLogout}
            className="text-sm text-[#718096] hover:text-red-500 transition-all"
          >
            退出
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* 左侧侧边栏 */}
        <aside className="w-[200px] bg-white border-r border-[#E2E8F0] flex flex-col flex-shrink-0">
          <nav className="flex-1 p-3 space-y-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                  location.pathname === item.path
                    ? 'bg-[#EBF0FF] text-[#6C8CFF] font-medium'
                    : 'text-[#718096] hover:bg-[#F5F7FA]'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </aside>

        {/* 中部主内容区 */}
        <main className={`flex-1 overflow-auto p-6 ${showRightPanel ? 'border-r border-[#E2E8F0]' : ''}`}>
          <Outlet />
        </main>

        {/* 右侧 AI 对话面板 */}
        {showRightPanel && (
          <aside className="w-[380px] bg-white flex flex-col flex-shrink-0">
            <ChatPanel />
          </aside>
        )}
      </div>
    </div>
  );
}

function ChatPanel() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/chat/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ question, mode: 'rag', kb_name: '' }),
      });

      if (!res.ok) throw new Error('请求失败');

      const reader = res.body?.getReader();
      if (!reader) return;

      let answer = '';
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setMessages((prev) => [...prev, { role: 'assistant', content: answer }]);
              setLoading(false);
              return;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === 'token') {
                answer += parsed.content;
              }
            } catch {
              answer += data;
            }
          }
        }
      }
    } catch (err: any) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <>
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#6C8CFF] text-white rounded-br-md'
                  : 'bg-[#F5F7FA] text-[#2D3748] rounded-bl-md'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#F5F7FA] px-4 py-2.5 rounded-2xl rounded-bl-md text-sm text-[#718096]">
              思考中...
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-[#E2E8F0]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            className="flex-1 px-4 py-2.5 border border-[#E2E8F0] rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF]"
            placeholder="输入你的问题..."
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-[#6C8CFF] hover:bg-[#5A7AE8] text-white rounded-xl text-sm transition-all disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </div>
    </>
  );
}
