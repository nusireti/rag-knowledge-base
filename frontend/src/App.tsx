import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/Login';
import { RegisterPage } from './pages/Register';
import { MainLayout } from './layouts/MainLayout';
import { KnowledgeBasesPage } from './pages/KnowledgeBases';
import { ChatPage } from './pages/Chat';

function App() {
  return (
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
  );
}

export default App;
