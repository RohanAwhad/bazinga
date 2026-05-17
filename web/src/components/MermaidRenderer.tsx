import { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'strict',
});

interface MermaidRendererProps {
  content: string;
}

export default function MermaidRenderer({ content }: MermaidRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const translateRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    translateRef.current = translate;
  }, [translate]);

  useEffect(() => {
    let cancelled = false;
    async function render() {
      if (!containerRef.current) return;
      setError(null);
      const id = `mermaid-${crypto.randomUUID()}`;
      try {
        const { svg } = await mermaid.render(id, content);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          if (containerRef.current) containerRef.current.innerHTML = '';
        }
      }
    }
    render();
    return () => { cancelled = true; };
  }, [content]);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale(s => Math.max(0.1, Math.min(5, s + delta)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setDragging(true);
    dragStart.current = { x: e.clientX - translateRef.current.x, y: e.clientY - translateRef.current.y };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return;
    setTranslate({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y,
    });
  }, [dragging]);

  const handleMouseUp = useCallback(() => {
    setDragging(false);
  }, []);

  return (
    <div
      className="mmd-preview"
      onWheel={handleWheel}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{ overflow: 'hidden', cursor: dragging ? 'grabbing' : 'grab', height: '100%' }}
    >
      {error && (
        <div style={{ color: '#f85149', padding: 16, fontFamily: 'monospace', fontSize: 13 }}>
          Mermaid parse error: {error}
        </div>
      )}
      <div
        ref={containerRef}
        style={{
          transform: `translate(${translate.x}px, ${translate.y}px) scale(${scale})`,
          transformOrigin: '0 0',
        }}
      />
    </div>
  );
}
