import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { auth } from '../api';

export function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [codeSent, setCodeSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    setLoading(true);
    setError('');
    try {
      const res = await auth.register(username.trim(), password, email, verifyCode);
      localStorage.setItem('token', res.token);
      localStorage.setItem('username', res.username);
      navigate('/app/knowledge-bases');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const sendCode = async () => {
    if (!email) return;
    try {
      await auth.sendVerifyCode(email);
      setCodeSent(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-[#F5F7FA] flex items-center justify-center p-4">
      <div className="w-full max-w-[400px] bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-8">
          <div className="text-4xl mb-3">🦝</div>
          <h1 className="text-xl font-semibold text-[#2D3748]">创建账号</h1>
          <p className="text-sm text-[#718096] mt-1">注册 RAG 智能知识库</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#4A5568] mb-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2.5 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF] transition-all"
              placeholder="至少2个字符"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#4A5568] mb-1">邮箱（可选）</label>
            <div className="flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="flex-1 px-4 py-2.5 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF] transition-all"
                placeholder="用于接收验证码"
              />
              <button
                type="button"
                onClick={sendCode}
                disabled={!email}
                className="px-3 py-2.5 bg-[#EDF2F7] hover:bg-[#E2E8F0] text-sm rounded-lg transition-all disabled:opacity-50"
              >
                发送
              </button>
            </div>
          </div>

          {codeSent && (
            <div>
              <label className="block text-sm font-medium text-[#4A5568] mb-1">验证码</label>
              <input
                type="text"
                value={verifyCode}
                onChange={(e) => setVerifyCode(e.target.value)}
                className="w-full px-4 py-2.5 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF] transition-all"
                placeholder="输入邮箱收到的验证码"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-[#4A5568] mb-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2.5 border border-[#E2E8F0] rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#6C8CFF] transition-all"
              placeholder="至少8位，需包含字母和数字"
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
            {loading ? '注册中...' : '注册'}
          </button>
        </form>

        <p className="text-center text-sm text-[#718096] mt-6">
          已有账号？
          <Link to="/login" className="text-[#6C8CFF] hover:underline ml-1">登录</Link>
        </p>
      </div>
    </div>
  );
}
