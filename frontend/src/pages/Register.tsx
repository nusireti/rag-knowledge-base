import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { auth, getErrorMessage } from '../api';
import { AuthShell } from '../components/AuthShell';
import { Button, Spinner } from '../components/ui';

export function RegisterPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [verifyCode, setVerifyCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [codeSent, setCodeSent] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, []);

  const startCooldown = () => {
    setCooldown(60);
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          if (timer.current) window.clearInterval(timer.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;

    setLoading(true);
    setError('');
    try {
      const res = await auth.register(
        username.trim(),
        password,
        email.trim(),
        verifyCode.trim(),
      );
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

  const sendCode = async () => {
    if (!email.trim()) return;
    setError('');
    try {
      await auth.sendVerifyCode(email.trim());
      setCodeSent(true);
      startCooldown();
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <AuthShell
      title="创建账号"
      subtitle="几步之后，你就可以上传文档并开始问答"
      footer={
        <>
          已有账号？
          <Link to="/login"> 去登录</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label className="label" htmlFor="reg-username">
            用户名
          </label>
          <input
            id="reg-username"
            className="input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="至少 2 个字符"
            autoComplete="username"
            autoFocus
          />
        </div>

        <div className="field">
          <label className="label" htmlFor="reg-email">
            邮箱 <span style={{ color: 'var(--ink-mute)' }}>（可选）</span>
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="reg-email"
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="用于接收验证码"
              autoComplete="email"
            />
            <Button
              size="sm"
              onClick={sendCode}
              disabled={!email.trim() || cooldown > 0}
              style={{ flexShrink: 0 }}
            >
              {cooldown > 0 ? `${cooldown}s` : codeSent ? '重发' : '发送'}
            </Button>
          </div>
        </div>

        {codeSent ? (
          <div className="field">
            <label className="label" htmlFor="reg-code">
              验证码
            </label>
            <input
              id="reg-code"
              className="input"
              type="text"
              value={verifyCode}
              onChange={(e) => setVerifyCode(e.target.value)}
              placeholder="输入邮箱收到的验证码"
              autoComplete="one-time-code"
            />
          </div>
        ) : null}

        <div className="field">
          <label className="label" htmlFor="reg-password">
            密码
          </label>
          <input
            id="reg-password"
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="至少 8 位，需包含字母和数字"
            autoComplete="new-password"
          />
          <div className="hint">至少 8 位，需同时包含字母和数字。</div>
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
              <Spinner size={14} /> 注册中
            </>
          ) : (
            '创建账号'
          )}
        </Button>
      </form>
    </AuthShell>
  );
}
