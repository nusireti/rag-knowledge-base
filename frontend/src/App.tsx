import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ToastProvider } from './components/ui';
import { MainLayout } from './layouts/MainLayout';
import { ChatPage } from './pages/Chat';
import { KnowledgeBasesPage } from './pages/KnowledgeBases';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/app" element={<MainLayout />}>
            <Route index element={<Navigate to="/app/knowledge-bases" replace />} />
            <Route path="knowledge-bases" element={<KnowledgeBasesPage />} />
            <Route path="chat" element={<ChatPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
}

export default App;
