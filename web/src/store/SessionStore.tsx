import { createContext, useContext, useReducer, type ReactNode, type Dispatch } from 'react';
import type { ChatMessage, ArtifactRef } from '../types';

interface SessionState {
  sessionId: string | null;
  messages: ChatMessage[];
  selectedArtifact: ArtifactRef | null;
}

type SessionAction =
  | { type: 'setSessionId'; sessionId: string | null }
  | { type: 'addMessage'; message: ChatMessage }
  | { type: 'appendChunk'; content: string }
  | { type: 'setSelectedArtifact'; artifact: ArtifactRef | null };

const initialState: SessionState = {
  sessionId: null,
  messages: [],
  selectedArtifact: null,
};

function sessionReducer(state: SessionState, action: SessionAction): SessionState {
  switch (action.type) {
    case 'setSessionId':
      return { ...state, sessionId: action.sessionId };
    case 'addMessage':
      return { ...state, messages: [...state.messages, action.message] };
    case 'appendChunk': {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + action.content };
      }
      return { ...state, messages: msgs };
    }
    case 'setSelectedArtifact':
      return { ...state, selectedArtifact: action.artifact };
    default:
      return state;
  }
}

const SessionStateContext = createContext<SessionState>(initialState);
const SessionDispatchContext = createContext<Dispatch<SessionAction>>(() => {});

export function SessionProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(sessionReducer, initialState);
  return (
    <SessionStateContext.Provider value={state}>
      <SessionDispatchContext.Provider value={dispatch}>
        {children}
      </SessionDispatchContext.Provider>
    </SessionStateContext.Provider>
  );
}

export function useSessionState() {
  return useContext(SessionStateContext);
}

export function useSessionDispatch() {
  return useContext(SessionDispatchContext);
}
