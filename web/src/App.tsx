import { useEffect, useRef, useState } from 'react';
import { useSessionState, useSessionDispatch } from './store/SessionStore';
import { WebSocketClient } from './clients/WebSocketClient';
import ChatPanel from './components/ChatPanel';
import ContentPanel from './components/ContentPanel';
import type { ConnectionStatus } from './types';
import './App.css';

const PROJECT_PATH = import.meta.env.VITE_PROJECT_PATH || '/repo';

function getWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/chat`;
}

export default function App() {
  const { sessionId } = useSessionState();
  const dispatch = useSessionDispatch();
  const wsRef = useRef<WebSocketClient>(new WebSocketClient());
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');

  useEffect(() => {
    const ws = wsRef.current;

    const unsubStatus = ws.onStatusChange((status) => {
      setConnectionStatus(status);
      if (status === 'disconnected') {
        dispatch({ type: 'setSessionId', sessionId: '' });
      }
    });

    const unsubSession = ws.onSession((sid: string) => {
      dispatch({ type: 'setSessionId', sessionId: sid });
    });

    const unsubMessage = ws.onMessage((payload) => {
      if (payload.type === 'done' && payload.content !== undefined) {
        dispatch({
          type: 'addMessage',
          message: {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: payload.content,
          },
        });
      } else if (payload.type === 'error' && payload.content) {
        dispatch({
          type: 'addMessage',
          message: {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Error: ${payload.content}`,
          },
        });
      }
    });

    ws.connect(getWsUrl());

    return () => {
      unsubStatus();
      unsubSession();
      unsubMessage();
      ws.disconnect();
    };
  }, [dispatch]);

  // Create session once connected
  useEffect(() => {
    if (connectionStatus === 'connected' && !sessionId) {
      wsRef.current.send({
        action: 'create_session',
        project_path: PROJECT_PATH,
      });
    }
  }, [connectionStatus, sessionId]);

  return (
    <>
      <div className="topbar">
        <span className="logo">bazinga</span>
        <span className="session">
          {sessionId ? `session: ${sessionId.slice(0, 12)}...` : 'no session'}
        </span>
        <span className={`status ${connectionStatus}`}>{connectionStatus}</span>
      </div>
      <div className="main">
        <ChatPanel
          wsClient={wsRef.current}
          connectionStatus={connectionStatus}
          projectPath={PROJECT_PATH}
        />
        <ContentPanel projectPath={PROJECT_PATH} />
      </div>
    </>
  );
}
