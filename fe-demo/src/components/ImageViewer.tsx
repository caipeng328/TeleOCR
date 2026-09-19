import { useEffect, useMemo, useState, type RefObject } from 'react';
import { HighlightOverlay } from '@/components/HighlightOverlay';
import { useContentWidth } from '@/hooks/useContentWidth';
import type { HighlightElement } from '@/types';
import { groupByPage } from '@/utils/parseElements';

interface ImageViewerProps {
  imageData: ArrayBuffer;
  mimeType: string;
  elements: HighlightElement[];
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
}

export function ImageViewer({
  imageData,
  mimeType,
  elements,
  activeId,
  onHover,
  onActivate,
  scrollRef,
  onScroll,
}: ImageViewerProps) {
  const displayWidth = useContentWidth(scrollRef);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const blob = new Blob([imageData.slice(0)], {
      type: mimeType || 'image/jpeg',
    });
    const url = URL.createObjectURL(blob);
    setBlobUrl(url);
    setLoadError(null);

    return () => {
      URL.revokeObjectURL(url);
      setBlobUrl((current) => (current === url ? null : current));
    };
  }, [imageData, mimeType]);

  // 单图当作第 0 页；OCR 没给页码时直接用整份元素
  const pageElements = useMemo(
    () => groupByPage(elements).get(0) ?? elements,
    [elements],
  );

  if (loadError) {
    return (
      <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-card">
        <p className="m-4 rounded-lg border border-destructive/50 p-3 text-sm text-destructive">
          {loadError}
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-card">
      <div
        className="min-h-0 flex-1 overflow-auto p-4"
        ref={scrollRef}
        onScroll={onScroll}
      >
        {blobUrl && displayWidth > 0 ? (
          <div className="pdf-pages">
            <div className="pdf-page-wrapper" data-page={0}>
              <img
                key={blobUrl}
                src={blobUrl}
                alt="上传图片"
                width={displayWidth}
                className="block h-auto max-w-full"
                onError={(e) => {
                  if (e.currentTarget.src !== blobUrl) return;
                  setLoadError('图片无法显示，请确认文件格式正确');
                }}
              />
              <HighlightOverlay
                elements={pageElements}
                activeId={activeId}
                onHover={onHover}
                onActivate={onActivate}
              />
            </div>
          </div>
        ) : (
          <p className="py-10 text-center text-sm text-muted-foreground">
            正在加载图片…
          </p>
        )}
      </div>
    </div>
  );
}
