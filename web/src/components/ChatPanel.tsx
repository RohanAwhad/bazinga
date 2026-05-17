import { useState, useRef, useEffect } from 'react';
import { useSessionState, useSessionDispatch } from '../store/SessionStore';
import type { ConnectionStatus, ArtifactRef } from '../types';
import type { WebSocketClient } from '../clients/WebSocketClient';
import './ChatPanel.css';

function extractArtifactRefs(content: string): ArtifactRef[] {
  const regex = /(\S+\.(?:md|mmd))/g;
  const refs: ArtifactRef[] = [];
  let match;
  while ((match = regex.exec(content)) !== null) {
    const path = match[1];
    if (!refs.some(r => r.path === path)) {
      refs.push({ path, label: path });
    }
  }
  return refs;
}

interface ChatPanelProps {
  wsClient: WebSocketClient;
  connectionStatus: ConnectionStatus;
  projectPath: string;
}

export default function ChatPanel({ wsClient, connectionStatus, projectPath }: ChatPanelProps) {
  const { messages, sessionId } = useSessionState();
  const dispatch = useSessionDispatch();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || !sessionId || connectionStatus !== 'connected') return;

    dispatch({
      type: 'addMessage',
      message: { id: crypto.randomUUID(), role: 'user', content: text },
    });

    wsClient.send({
      project_path: projectPath,
      session_id: sessionId,
      message: text,
    });

    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleArtifactClick = (ref: ArtifactRef) => {
    dispatch({ type: 'setSelectedArtifact', artifact: ref });
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">Chat</div>
      <div className="messages">
        {messages.map(msg => {
          const refs = msg.role === 'assistant' ? extractArtifactRefs(msg.content) : [];
          return (
            <div key={msg.id} className={`msg ${msg.role}`}>
              <span>{msg.content}</span>
              {refs.map(ref => (
                <span
                  key={ref.path}
                  className="artifact-ref"
                  onClick={() => handleArtifactClick(ref)}
                >
                  {ref.label}
                </span>
              ))}
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input">
        <input
          type="text"
          placeholder="Ask about the design..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          onClick={handleSend}
          disabled={connectionStatus !== 'connected' || !sessionId}
        >
          Send
        </button>
      </div>
    </div>
  );
}
