import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { SessionProvider } from './store/SessionStore';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SessionProvider>
      <App />
    </SessionProvider>
  </StrictMode>,
);
