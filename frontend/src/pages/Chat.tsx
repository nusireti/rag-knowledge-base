import { useState } from 'react';

export function ChatPage() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="text-5xl mb-4">💬</div>
        <h2 className="text-lg font-semibold text-[#2D3748] mb-2">AI 智能问答</h2>
        <p className="text-sm text-[#718096]">
          在右侧面板中开始对话，或从知识库页面进入问答
        </p>
      </div>
    </div>
  );
}
