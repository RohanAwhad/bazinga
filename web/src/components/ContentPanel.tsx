import { useEffect, useState, useMemo } from 'react';
import { useSessionState, useSessionDispatch } from '../store/SessionStore';
import { listArtifacts, fetchArtifact } from '../clients/ArtifactClient';
import MarkdownRenderer from './MarkdownRenderer';
import MermaidRenderer from './MermaidRenderer';
import type { ArtifactEntry } from '../types';
import './ContentPanel.css';

interface ContentPanelProps {
  projectPath: string;
}

export default function ContentPanel({ projectPath }: ContentPanelProps) {
  const { selectedArtifact } = useSessionState();
  const dispatch = useSessionDispatch();
  const [artifacts, setArtifacts] = useState<ArtifactEntry[]>([]);
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listArtifacts(projectPath)
      .then(setArtifacts)
      .catch(err => {
        console.error('Failed to list artifacts:', err);
        setArtifacts([]);
      });
  }, [projectPath]);

  useEffect(() => {
    if (!selectedArtifact) {
      setContent('');
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    fetchArtifact(projectPath, selectedArtifact.path)
      .then(text => {
        setContent(text);
      })
      .catch(err => {
        console.error('Failed to fetch artifact:', err);
        setContent('');
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        setLoading(false);
      });
  }, [selectedArtifact, projectPath]);

  const grouped = useMemo(() => {
    const groups: Record<string, ArtifactEntry[]> = {};
    for (const a of artifacts) {
      const parts = a.path.split('/');
      const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '.';
      if (!groups[dir]) groups[dir] = [];
      groups[dir].push(a);
    }
    return groups;
  }, [artifacts]);

  const isMmd = selectedArtifact?.path.endsWith('.mmd');
  const isMd = selectedArtifact?.path.endsWith('.md');
  const badgeClass = isMmd ? 'badge mmd' : 'badge md';
  const badgeText = isMmd ? 'MMD' : 'MD';

  if (!selectedArtifact) {
    return (
      <div className="content">
        <div className="content-header">
          <span className="filepath">Artifacts</span>
        </div>
        <div className="content-body">
          <div className="artifact-list">
            {Object.entries(grouped).map(([dir, entries]) => (
              <div key={dir} className="artifact-group">
                <div className="artifact-group-header">{dir}/</div>
                {entries.map(entry => (
                  <div
                    key={entry.path}
                    className="artifact-list-item"
                    onClick={() =>
                      dispatch({
                        type: 'setSelectedArtifact',
                        artifact: { path: entry.path, label: entry.name },
                      })
                    }
                  >
                    <span className={entry.type === 'mmd' ? 'badge mmd' : 'badge md'}>
                      {entry.type.toUpperCase()}
                    </span>
                    <span className="artifact-name">{entry.name}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="content">
      <div className="content-header">
        <span className={badgeClass}>{badgeText}</span>
        <span className="filepath">{selectedArtifact.path}</span>
      </div>
      <div className="content-body">
        {loading ? (
          <div style={{ color: '#8b949e', padding: 24 }}>Loading...</div>
        ) : error ? (
          <div style={{ color: '#f85149', padding: 24 }}>Error: {error}</div>
        ) : isMmd ? (
          <MermaidRenderer content={content} />
        ) : isMd ? (
          <MarkdownRenderer content={content} />
        ) : (
          <pre style={{ color: '#c9d1d9', whiteSpace: 'pre-wrap' }}>{content}</pre>
        )}
      </div>
    </div>
  );
}
