import { useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  LogOut,
  MessageSquareText,
  Sparkles,
} from 'lucide-react';
import { ApiError, auth as authApi } from '../api';

const NAV_ITEMS = [
  {
    path: '/app/knowledge-bases',
    label: '知识库',
    num: '01',
    icon: BookOpen,
  },
  {
    path: '/app/chat',
    label: 'AI 问答',
    num: '02',
    icon: MessageSquareText,
  },
];

export function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState(
    localStorage.getItem('username') || '用户',
  );
  const [displayName, setDisplayName] = useState('');
  const [menuOpen, setMenuOpen] = useState(false);

  const isChat = location.pathname.startsWith('/app/chat');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/login', { replace: true });
      return;
    }
    authApi
      .getMe()
      .then((me) => {
        setUsername(me.username || username);
        setDisplayName(me.display_name || '');
      })
      .catch((err) => {
        // Token 失效：清掉本地状态回登录页
        if (err instanceof ApiError && err.status === 401) {
          localStorage.removeItem('token');
          localStorage.removeItem('username');
          navigate('/login', { replace: true });
        }
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login', { replace: true });
  };

  const shownName = displayName || username;
  const avatar = shownName.slice(0, 1).toUpperCase();
  const today = new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    weekday: 'short',
  }).format(new Date());

  return (
    <>
      <div className="topbar">
        <b>RAG 知识库</b>
        <button onClick={() => setMenuOpen((v) => !v)}>
          {menuOpen ? '关闭' : '目录'}
        </button>
      </div>

      <div className="app-shell">
        {menuOpen && (
          <div className="side-backdrop" onClick={() => setMenuOpen(false)} />
        )}

        <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
          <div className="brand">
            <div className="brand-mark">知</div>
            <h1>RAG 知识库</h1>
            <div className="who">
              nusireti · 大连海洋大学
              <br />
              AI 应用开发 · 2027 届
            </div>
          </div>

          <nav className="side-nav">
            <div className="nav-group">WORKSPACE</div>
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = location.pathname.startsWith(item.path);
              return (
                <button
                  key={item.path}
                  className={`nav-link ${active ? 'active' : ''}`}
                  onClick={() => {
                    setMenuOpen(false);
                    navigate(item.path);
                  }}
                >
                  <Icon size={15} />
                  <span>{item.label}</span>
                  <span className="nav-num">{item.num}</span>
                </button>
              );
            })}

            <div className="nav-group">STACK</div>
            <div
              className="nav-link"
              style={{ cursor: 'default', color: '#8fa9a3' }}
            >
              <Sparkles size={15} />
              <span>混合检索 · Agent</span>
            </div>
            <div
              className="nav-link"
              style={{ cursor: 'default', color: '#8fa9a3' }}
            >
              <span style={{ width: 15 }} />
              <span>多模型可切换</span>
            </div>
          </nav>

          <div className="side-foot">
            <div className="side-status">
              今天 <b>{today}</b>
              <br />
              系统在线 · 向量库就绪
            </div>
            <div className="side-user">
              <div className="side-avatar">{avatar}</div>
              <div>
                <div className="u-name">{shownName}</div>
                <div className="u-role">AI 应用开发</div>
              </div>
              <button
                className="side-logout"
                onClick={handleLogout}
                title="退出登录"
              >
                <LogOut size={12} />
              </button>
            </div>
          </div>
        </aside>

        <main className={`main ${isChat ? 'main-full' : ''}`}>
          <div className="main-inner">
            <Outlet />
          </div>
        </main>
      </div>
    </>
  );
}
