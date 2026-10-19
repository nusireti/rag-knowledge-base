import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { auth, getErrorMessage } from '../api';
import { AuthShell } from '../components/AuthShell';
import { Button, Spinner } from '../components/ui';

export function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;

    setLoading(true);
    setError('');
    try {
      const res = await auth.login(username.trim(), password);
      localStorage.setItem('token', res.token);
      localStorage.setItem('username', res.username);
      localStorage.setItem('display_name', res.display_name);
      navigate('/app/knowledge-bases', { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="登录工作台"
      subtitle="继续你的知识库、文档与问答"
      footer={
        <>
          还没有账号？
          <Link to="/register"> 注册一个</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label className="label" htmlFor="login-username">
            用户名
          </label>
          <input
            id="login-username"
            className="input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="输入用户名"
            autoComplete="username"
            autoFocus
          />
        </div>

        <div className="field">
          <label className="label" htmlFor="login-password">
            密码
          </label>
          <input
            id="login-password"
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="输入密码"
            autoComplete="current-password"
          />
        </div>

        {error ? <div className="form-error">{error}</div> : null}

        <Button
          type="submit"
          variant="primary"
          className="btn-block"
          disabled={loading || !username.trim() || !password}
        >
          {loading ? (
            <>
              <Spinner size={14} /> 登录中
            </>
          ) : (
            '登录'
          )}
        </Button>
      </form>
    </AuthShell>
  );
}
