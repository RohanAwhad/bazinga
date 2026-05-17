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

export interface WsSendPayload {
  type: 'chat';
  sessionId: string;
  content: string;
}

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
