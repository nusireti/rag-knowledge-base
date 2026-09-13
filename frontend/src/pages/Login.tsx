import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { auth } from '../api';

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError('');
    try {
      const res = await auth.login(username.trim(), password);
      localStorage.setItem('token', res.token);
      localStorage.setItem('username', res.username);
      navigate('/app/knowledge-bases');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center p-4">
      <div className="w-full max-w-[400px] bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🦝</div>
          <h1 className="text-xl font-semibold text-[#2D3748]">RAG 智能知识库</h1>
          <p className="text-sm text-[#718096] mt-1">登录你的账号</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#4A5568] mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF] focus:border-transparent transition-all"
              placeholder="输入用户名"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#4A5568] mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF] focus:border-transparent transition-all"
              placeholder="输入密码"
            />
          </div>

          {error && (
            <div className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-[#6C8CFF] hover:bg-[#5A7AE8] text-white font-medium rounded-lg text-sm transition-all disabled:opacity-50"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>

        <p className="text-center text-sm text-[#718096] mt-6">
          还没有账号？
          <Link to="/register" className="text-[#6C8CFF] hover:underline ml-1">注册</Link>
        </p>
      </div>
    </div>
  );
}
