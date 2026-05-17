export const ARTIFACT_EXT_MMD = '.mmd';
export const ARTIFACT_EXT_MD = '.md';

export interface ArtifactRef {
  path: string;
  label: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  artifactRefs?: ArtifactRef[];
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WsSendChat {
  project_path: string;
  session_id: string;
  message: string;
}

export interface WsSendCreateSession {
  action: 'create_session';
  project_path: string;
}

export type WsSendPayload = WsSendChat | WsSendCreateSession;

export interface WsReceivePayload {
  type: 'chunk' | 'done' | 'error';
  content?: string;
  artifactRefs?: ArtifactRef[];
}

export interface ArtifactEntry {
  name: string;
  path: string;
  type: string;
}
