const API_BASE = '/api';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  if (options?.headers) {
    Object.assign(headers, options.headers);
  }
  if (options?.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new ApiError(
      (err as { detail?: string }).detail || `HTTP ${res.status}`,
      res.status,
    );
  }
  return res.json() as Promise<T>;
}

export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

/* ------------------------------------------------------------------ */
/* Auth                                                                */
/* ------------------------------------------------------------------ */
export interface UserInfo {
  user_id: string;
  username: string;
  display_name: string;
  email?: string;
  is_admin?: boolean;
}

export interface LoginResponse {
  token: string;
  user_id: string;
  username: string;
  display_name: string;
}

export const auth = {
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  register: (
    username: string,
    password: string,
    email?: string,
    verify_code?: string,
  ) =>
    request<LoginResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username,
        password,
        email: email || '',
        verify_code: verify_code || '',
      }),
    }),
  sendVerifyCode: (email: string) =>
    request<{ message: string }>('/auth/verify-code', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  getMe: () => request<UserInfo>('/auth/me'),
  capabilities: () =>
    request<{ email_verification: boolean }>('/auth/capabilities'),
};

/* ------------------------------------------------------------------ */
/* Knowledge bases                                                     */
/* ------------------------------------------------------------------ */
export interface KnowledgeBase {
  name: string;
  display_name: string;
  description?: string;
  doc_count?: number;
}

export const kb = {
  list: () => request<{ data: KnowledgeBase[] }>('/knowledge-bases/'),
  get: (name: string) => request<{ data: KnowledgeBase }>(`/knowledge-bases/${name}`),
  create: (name: string, display_name?: string, description?: string) =>
    request<{ message: string }>('/knowledge-bases/', {
      method: 'POST',
      body: JSON.stringify({
        name,
        display_name: display_name || name,
        description: description || '',
      }),
    }),
  delete: (name: string) =>
    request<{ message: string }>(`/knowledge-bases/${name}`, { method: 'DELETE' }),
};

/* ------------------------------------------------------------------ */
/* Documents                                                           */
/* ------------------------------------------------------------------ */
export interface DocumentInfo {
  name: string;
  size_str?: string;
  size?: number;
}

export interface UploadResult {
  message: string;
  filename: string;
  indexed: number;
}

export const docs = {
  list: (kb_name: string) =>
    request<{ data: DocumentInfo[] }>(
      `/documents/?kb_name=${encodeURIComponent(kb_name)}`,
    ),
  upload: (kb_name: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<UploadResult>(
      `/documents/upload?kb_name=${encodeURIComponent(kb_name)}`,
      { method: 'POST', body: fd },
    );
  },
  delete: (kb_name: string, filename: string) =>
    request<{ message: string }>(
      `/documents/?kb_name=${encodeURIComponent(kb_name)}&filename=${encodeURIComponent(filename)}`,
      { method: 'DELETE' },
    ),
  rebuild: (kb_name: string) =>
    request<{ message: string; chunks: number }>(
      `/documents/rebuild?kb_name=${encodeURIComponent(kb_name)}`,
      { method: 'POST' },
    ),
  preview: (kb_name: string, filename: string, max_chars = 4000) =>
    request<{ content: string }>(
      `/documents/preview?kb_name=${encodeURIComponent(kb_name)}&filename=${encodeURIComponent(filename)}&max_chars=${max_chars}`,
    ),
};

/* ------------------------------------------------------------------ */
/* Chat                                                                */
/* ------------------------------------------------------------------ */
export interface Conversation {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
  message_count?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | string;
  content: string;
}

export interface AskPayload {
  question: string;
  kb_name: string;
  mode: 'rag' | 'agent';
  conv_id?: string;
  hybrid_search?: boolean;
}

export const chat = {
  listConversations: () =>
    request<{ data: Conversation[] }>('/chat/conversations'),
  createConversation: () =>
    request<{ conv_id: string; title: string }>('/chat/conversations', {
      method: 'POST',
    }),
  deleteConversation: (id: string) =>
    request<{ message: string }>(`/chat/conversations/${id}`, {
      method: 'DELETE',
    }),
  getConversation: (id: string) =>
    request<{ data: { id: string; messages: ChatMessage[] } }>(
      `/chat/conversations/${id}`,
    ),
  exportConversation: (id: string, fmt: 'md' | 'txt' = 'md') =>
    request<{ content: string }>(`/chat/conversations/${id}/export?fmt=${fmt}`),
};

/** 发起流式问答，返回原始 Response，由调用方用 readSSE 消费。 */
export async function streamAsk(payload: AskPayload): Promise<Response> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}/chat/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      question: payload.question,
      kb_name: payload.kb_name,
      mode: payload.mode,
      conv_id: payload.conv_id || '',
      hybrid_search: payload.hybrid_search ?? true,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '请求失败' }));
    throw new ApiError(
      (err as { detail?: string }).detail || `HTTP ${res.status}`,
      res.status,
    );
  }
  return res;
}

/* ------------------------------------------------------------------ */
/* Models                                                              */
/* ------------------------------------------------------------------ */
export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

export const models = {
  list: () => request<{ data: ModelInfo[] }>('/models/'),
};
