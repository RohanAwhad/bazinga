import type { ConnectionStatus, WsReceivePayload } from '../types';

type MessageHandler = (payload: WsReceivePayload) => void;
type SessionHandler = (sessionId: string) => void;
type StatusHandler = (status: ConnectionStatus) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private messageHandlers: MessageHandler[] = [];
  private sessionHandlers: SessionHandler[] = [];
  private statusHandlers: StatusHandler[] = [];
  private _status: ConnectionStatus = 'disconnected';
  private _url: string | null = null;
  private _reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _reconnectAttempt = 0;
  private _intentionalClose = false;

  private static readonly MAX_RECONNECT_DELAY = 30000;
  private static readonly BASE_RECONNECT_DELAY = 1000;

  get status(): ConnectionStatus {
    return this._status;
  }

  private setStatus(status: ConnectionStatus) {
    this._status = status;
    this.statusHandlers.forEach(h => h(status));
  }

  connect(url: string) {
    this._url = url;
    this._intentionalClose = false;
    this._reconnectAttempt = 0;
    this._doConnect();
  }

  private _doConnect() {
    if (!this._url) return;
    this.setStatus('connecting');
    this.ws = new WebSocket(this._url);

    this.ws.onopen = () => {
      this._reconnectAttempt = 0;
      this.setStatus('connected');
    };

    this.ws.onclose = () => {
      this.setStatus('disconnected');
      if (!this._intentionalClose) {
        this._scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      this.setStatus('error');
    };

    this.ws.onmessage = (event: MessageEvent) => {
      let data: Record<string, unknown>;
      try {
        data = JSON.parse(event.data);
      } catch {
        const payload: WsReceivePayload = {
          type: 'error',
          content: 'Received malformed message from server',
        };
        this.messageHandlers.forEach(h => h(payload));
        return;
      }

      // Handle session creation response
      if (data.session_id) {
        this.sessionHandlers.forEach(h => h(data.session_id as string));
        return;
      }

      // Handle error response
      if (data.error) {
        const payload: WsReceivePayload = { type: 'error', content: data.error as string };
        this.messageHandlers.forEach(h => h(payload));
        return;
      }

      // Handle chat response (single complete response from backend)
      if (data.response !== undefined) {
        const payload: WsReceivePayload = { type: 'done', content: data.response as string };
        this.messageHandlers.forEach(h => h(payload));
        return;
      }
    };
  }

  private _scheduleReconnect() {
    if (this._reconnectTimer) return;
    const delay = Math.min(
      WebSocketClient.BASE_RECONNECT_DELAY * 2 ** this._reconnectAttempt,
      WebSocketClient.MAX_RECONNECT_DELAY,
    );
    this._reconnectAttempt++;
    this._reconnectTimer = setTimeout(() => {
      this._reconnectTimer = null;
      this._doConnect();
    }, delay);
  }

  disconnect() {
    this._intentionalClose = true;
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(payload: Record<string, unknown>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.push(handler);
    return () => {
      this.messageHandlers = this.messageHandlers.filter(h => h !== handler);
    };
  }

  onSession(handler: SessionHandler): () => void {
    this.sessionHandlers.push(handler);
    return () => {
      this.sessionHandlers = this.sessionHandlers.filter(h => h !== handler);
    };
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusHandlers.push(handler);
    return () => {
      this.statusHandlers = this.statusHandlers.filter(h => h !== handler);
    };
  }
}
