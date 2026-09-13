const API_BASE = '/api';

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
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// === Auth ===
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
  register: (username: string, password: string, email?: string, verify_code?: string) =>
    request<LoginResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, email: email || '', verify_code: verify_code || '' }),
    }),
  sendVerifyCode: (email: string) =>
    request<{ message: string }>('/auth/verify-code', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  getMe: () => request<UserInfo>('/auth/me'),
};

// === Knowledge Bases ===
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
      body: JSON.stringify({ name, display_name: display_name || name, description: description || '' }),
    }),
  delete: (name: string) =>
    request<{ message: string }>(`/knowledge-bases/${name}`, { method: 'DELETE' }),
};

// === Documents ===
export interface DocumentInfo {
  name: string;
  size_str?: string;
}

export const docs = {
  list: (kb_name: string) =>
    request<{ data: DocumentInfo[] }>(`/documents/?kb_name=${kb_name}`),
  upload: (kb_name: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return request<{ message: string; filename: string }>(`/documents/upload?kb_name=${kb_name}`, {
      method: 'POST',
      body: fd,
    });
  },
  delete: (kb_name: string, filename: string) =>
    request<{ message: string }>(`/documents/?kb_name=${kb_name}&filename=${filename}`, { method: 'DELETE' }),
  rebuild: (kb_name: string) =>
    request<{ message: string }>(`/documents/rebuild?kb_name=${kb_name}`, { method: 'POST' }),
  preview: (kb_name: string, filename: string) =>
    request<{ content: string }>(`/documents/preview?kb_name=${kb_name}&filename=${filename}`),
};

// === Chat ===
export interface Conversation {
  id: string;
  title: string;
}

export const chat = {
  listConversations: () => request<{ data: Conversation[] }>('/chat/conversations'),
  createConversation: () => request<{ conv_id: string; title: string }>('/chat/conversations', { method: 'POST' }),
  deleteConversation: (id: string) =>
    request<{ message: string }>(`/chat/conversations/${id}`, { method: 'DELETE' }),
  getConversation: (id: string) =>
    request<{ data: { id: string; messages: any[] } }>(`/chat/conversations/${id}`),
};
