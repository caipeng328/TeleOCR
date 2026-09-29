import type { HighlightElement } from '@/types';
import { bboxToPercent } from '@/utils/parseElements';

interface HighlightOverlayProps {
  elements: HighlightElement[];
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
}

/** 铺满页面容器的 bbox 高亮层，坐标用百分比，随面板缩放自动对齐 */
export function HighlightOverlay({
  elements,
  activeId,
  onHover,
  onActivate,
}: HighlightOverlayProps) {
  return (
    <div className="pdf-overlay">
      {elements.map((el) => (
        <div
          key={el.id}
          className={`highlight-overlay ${activeId === el.id ? 'active' : ''}`}
          style={bboxToPercent(el.bbox, el.pageSize)}
          data-id={el.id}
          title={el.content.slice(0, 80)}
          onMouseEnter={() => onHover(el.id)}
          onMouseLeave={() => onHover(null)}
          onClick={(e) => {
            e.stopPropagation();
            onActivate(el.id);
          }}
        />
      ))}
    </div>
  );
}
