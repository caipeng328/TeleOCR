import { useMemo, useState, type RefObject } from 'react';
import { Document, Page } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { HighlightOverlay } from '@/components/HighlightOverlay';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Spinner } from '@/components/ui/spinner';
import { useContentWidth } from '@/hooks/useContentWidth';
import type { HighlightElement } from '@/types';
import { groupByPage } from '@/utils/parseElements';
import { configurePdfWorker } from '@/utils/pdfWorker';

configurePdfWorker();

interface PdfViewerProps {
  pdfData: ArrayBuffer;
  /** OCR 给出的页数；为 0 时回退到 pdf.js 自己读出的页数 */
  pageCount: number;
  elements: HighlightElement[];
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
}

export function PdfViewer({
  pdfData,
  pageCount,
  elements,
  activeId,
  onHover,
  onActivate,
  scrollRef,
  onScroll,
}: PdfViewerProps) {
  const pageWidth = useContentWidth(scrollRef);
  const [detectedPages, setDetectedPages] = useState(0);

  // 交给 pdf.js 前先复制一份：worker 会 transfer 掉这个 buffer
  const pdfFile = useMemo(
    () => ({ data: new Uint8Array(pdfData.slice(0)) }),
    [pdfData],
  );

  const elementsByPage = groupByPage(elements);
  const pageIndices = Array.from(
    { length: pageCount > 0 ? pageCount : detectedPages },
    (_, i) => i,
  );

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-card">
      <div
        className="min-h-0 flex-1 overflow-auto p-4"
        ref={scrollRef}
        onScroll={onScroll}
      >
        {pageWidth > 0 && (
          <Document
            file={pdfFile}
            loading={
              <div className="flex justify-center py-10">
                <Spinner label="加载 PDF…" />
              </div>
            }
            error={
              <Alert variant="destructive" className="m-4">
                <AlertDescription>
                  PDF 无法打开，请确认文件未损坏
                </AlertDescription>
              </Alert>
            }
            onLoadSuccess={({ numPages }) => setDetectedPages(numPages)}
          >
            <div className="pdf-pages">
              {pageIndices.map((pageIdx) => (
                <div
                  key={pageIdx}
                  className="pdf-page-wrapper"
                  data-page={pageIdx}
                >
                  <Page
                    pageNumber={pageIdx + 1}
                    width={pageWidth}
                    renderTextLayer={false}
                    renderAnnotationLayer={false}
                  />
                  <HighlightOverlay
                    elements={elementsByPage.get(pageIdx) ?? []}
                    activeId={activeId}
                    onHover={onHover}
                    onActivate={onActivate}
                  />
                </div>
              ))}
            </div>
          </Document>
        )}
      </div>
    </div>
  );
}
