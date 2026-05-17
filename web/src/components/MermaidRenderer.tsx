import { useEffect, useRef, useState, useCallback } from 'react';
import mermaid from 'mermaid';

const MIN_SCALE = 0.1;
const MAX_SCALE = 5;
const ZOOM_STEP = 0.1;

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'strict',
});

interface MermaidRendererProps {
  content: string;
}

export default function MermaidRenderer({ content }: MermaidRendererProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [translate, setTranslate] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const draggingRef = useRef(false);
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

  // Use native addEventListener with { passive: false } so preventDefault() works on wheel events.
  // React's onWheel attaches a passive listener, making preventDefault() a no-op.
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    function onWheel(e: WheelEvent) {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
      setScale(s => Math.max(MIN_SCALE, Math.min(MAX_SCALE, s + delta)));
    }
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    draggingRef.current = true;
    setDragging(true);
    dragStart.current = { x: e.clientX - translateRef.current.x, y: e.clientY - translateRef.current.y };
  }, []);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!draggingRef.current) return;
    setTranslate({
      x: e.clientX - dragStart.current.x,
      y: e.clientY - dragStart.current.y,
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    draggingRef.current = false;
    setDragging(false);
  }, []);

  return (
    <div
      ref={wrapperRef}
      className="mmd-preview"
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
