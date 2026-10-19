import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type ReactNode,
} from 'react';
import { Loader2, X } from 'lucide-react';

/* ------------------------------------------------------------------ */
/* Button                                                              */
/* ------------------------------------------------------------------ */
type ButtonVariant = 'default' | 'primary' | 'dark' | 'danger' | 'ghost';
type ButtonSize = 'sm' | 'md' | 'icon';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClass: Record<ButtonVariant, string> = {
  default: '',
  primary: 'btn-primary',
  dark: 'btn-dark',
  danger: 'btn-danger',
  ghost: 'btn-ghost',
};

const sizeClass: Record<ButtonSize, string> = {
  sm: 'btn-sm',
  md: '',
  icon: 'btn-icon',
};

export function Button({
  variant = 'default',
  size = 'md',
  className = '',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={`btn ${variantClass[variant]} ${sizeClass[size]} ${className}`}
      {...props}
    />
  );
}

/* ------------------------------------------------------------------ */
/* Card / Tag / Stat                                                   */
/* ------------------------------------------------------------------ */
export function Card({
  children,
  className = '',
  accent,
}: {
  children: ReactNode;
  className?: string;
  accent?: 'teal' | 'rust' | 'gold' | 'neutral';
}) {
  const accentClass = accent ? `card-accent ${accent === 'teal' ? '' : accent}` : '';
  return <div className={`card ${accentClass} ${className}`}>{children}</div>;
}

export function Tag({
  children,
  tone = 'teal',
}: {
  children: ReactNode;
  tone?: 'teal' | 'gold' | 'rust' | 'neutral';
}) {
  return <span className={`tag ${tone === 'teal' ? '' : tone}`}>{children}</span>;
}

export function Stat({
  value,
  label,
  suffix,
}: {
  value: ReactNode;
  label: string;
  suffix?: string;
}) {
  return (
    <div className="stat">
      <div className="n">
        {value}
        {suffix ? <small>{suffix}</small> : null}
      </div>
      <div className="l">{label}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Page header                                                         */
/* ------------------------------------------------------------------ */
export function PageHeader({
  kicker,
  title,
  subtitle,
  actions,
  right,
}: {
  kicker: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  right?: ReactNode;
}) {
  return (
    <header className="page-head">
      <div className="head-row">
        <div>
          <div className="kicker">{kicker}</div>
          <h1 className="page-title">{title}</h1>
          {subtitle ? <p className="page-sub">{subtitle}</p> : null}
        </div>
        {right}
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Modal                                                               */
/* ------------------------------------------------------------------ */
export function Modal({
  open,
  title,
  subtitle,
  onClose,
  children,
  footer,
  wide = false,
}: {
  open: boolean;
  title: string;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className={`modal ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true">
        <div className="modal-head">
          <div>
            <h3>{title}</h3>
            {subtitle ? <div className="modal-sub">{subtitle}</div> : null}
          </div>
          <button className="modal-close" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        {children}
        {footer ? <div className="modal-actions">{footer}</div> : null}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Empty / Spinner                                                     */
/* ------------------------------------------------------------------ */
export function Empty({
  icon,
  title,
  desc,
  action,
}: {
  icon: ReactNode;
  title: string;
  desc?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="glyph">{icon}</div>
      <h3>{title}</h3>
      {desc ? <p>{desc}</p> : null}
      {action}
    </div>
  );
}

export function Spinner({ size = 16 }: { size?: number }) {
  return <Loader2 size={size} className="spin" />;
}

export function Skeleton({ height = 16, width = '100%' }: { height?: number; width?: string }) {
  return <div className="skeleton" style={{ height, width }} />;
}

/* ------------------------------------------------------------------ */
/* Toast                                                               */
/* ------------------------------------------------------------------ */
type ToastTone = 'info' | 'success' | 'error';
interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastApi {
  push: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);

  const push = useCallback((message: string, tone: ToastTone = 'info') => {
    seq.current += 1;
    const id = seq.current;
    setItems((prev) => [...prev, { id, message, tone }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 3400);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toast-wrap">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
