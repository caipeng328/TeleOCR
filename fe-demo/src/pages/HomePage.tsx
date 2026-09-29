import { useEffect, useRef, useState } from 'react';
import { Loader2, ScanText } from 'lucide-react';
import { toast } from 'sonner';
import { inferOcr, type InferStage } from '@/api/inferOcr';
import { IconSwap } from '@/components/IconSwap';
import { ImageViewer } from '@/components/ImageViewer';
import { MarkdownResultPanel } from '@/components/MarkdownResultPanel';
import { PanelToolbar } from '@/components/PanelToolbar';
import { PdfViewer } from '@/components/PdfViewer';
import { SourceDropzone } from '@/components/SourceDropzone';
import { Button } from '@/components/ui/button';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable';
import { Spinner } from '@/components/ui/spinner';
import { useHoverSync } from '@/hooks/useHoverSync';
import { useOcrDocument } from '@/hooks/useOcrDocument';
import { useScrollSync } from '@/hooks/useScrollSync';
import type { DocumentConfig, PdfOcrData } from '@/types';
import {
  resolveSourceKind,
  SOURCE_ACCEPT,
  stripExtension,
  type SourceKind,
} from '@/utils/sourceFile';

const STAGE_LABEL: Record<InferStage, string> = {
  encoding: '正在编码文件…',
  uploading: '正在上传并解析…',
  parsing: '正在处理 OCR 结果…',
};

/** 本地选中的文件，仅用于在解析完成前先把原文显示出来 */
interface SourceFile {
  kind: SourceKind;
  name: string;
  previewData: ArrayBuffer;
  mimeType: string;
}

function buildUploadedConfig(
  source: SourceFile,
  data: ArrayBuffer,
  ocrData: PdfOcrData,
): DocumentConfig {
  const base = { id: 'uploaded', title: source.name, ocrData };

  return source.kind === 'pdf'
    ? { ...base, description: '本地上传 · PDF OCR 解析', pdfData: data }
    : {
        ...base,
        description: '本地上传 · 图片 OCR 解析',
        imageData: data,
        imageMimeType: source.mimeType,
      };
}

/** 原文面板当前要显示的内容 */
type SourcePreview =
  | { kind: 'pdf'; data: ArrayBuffer }
  | { kind: 'image'; data: ArrayBuffer; mimeType: string };

/** 解析完成前先显示本地选中的文件，完成后切到 config 里那份 */
function resolvePreview(
  source: SourceFile | null,
  config: DocumentConfig | null,
): SourcePreview | null {
  if (source) {
    return source.kind === 'pdf'
      ? { kind: 'pdf', data: source.previewData }
      : { kind: 'image', data: source.previewData, mimeType: source.mimeType };
  }
  if (config?.imageData) {
    return {
      kind: 'image',
      data: config.imageData,
      mimeType: config.imageMimeType ?? 'image/jpeg',
    };
  }
  if (config?.pdfData) {
    return { kind: 'pdf', data: config.pdfData };
  }
  return null;
}

export function HomePage() {
  const [source, setSource] = useState<SourceFile | null>(null);
  const [config, setConfig] = useState<DocumentConfig | null>(null);
  /** null = 空闲，否则为当前解析阶段 */
  const [stage, setStage] = useState<InferStage | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [contentKey, setContentKey] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const parsing = stage !== null;
  const { data, error: ocrError } = useOcrDocument(config);
  const parsedReady = data !== null && ocrError === null;

  const { setHover, registerSetter } = useHoverSync();
  const {
    pdfScrollRef,
    mdScrollRef,
    scrollToId,
    handlePdfScroll,
    handleMdScroll,
  } = useScrollSync();

  useEffect(() => {
    registerSetter(setActiveId);
  }, [registerSetter]);

  useEffect(() => {
    if (ocrError) toast.error(ocrError);
  }, [ocrError]);

  const preview = resolvePreview(source, config);

  function handleActivate(id: string) {
    setHover(id);
    scrollToId(id, 'smooth');
  }

  async function processFile(file: File) {
    const kind = resolveSourceKind(file);
    if (!kind) {
      toast.error('请选择 PDF 或图片文件（PNG、JPG、WebP 等）');
      return;
    }

    setActiveId(null);
    setConfig(null);
    setStage('encoding');

    try {
      const fileData = await file.arrayBuffer();
      // 分成两份：pdf.js 会 transfer 掉预览用的那个 buffer
      const previewData = fileData.slice(0);
      const apiData = fileData.slice(0);

      const nextSource: SourceFile = {
        kind,
        name: stripExtension(file.name),
        previewData,
        mimeType:
          file.type || (kind === 'pdf' ? 'application/pdf' : 'image/jpeg'),
      };
      setSource(nextSource);

      const ocrData = await inferOcr(apiData, {
        imageType: kind === 'pdf' ? 1 : 2,
        onProgress: setStage,
      });

      setConfig(buildUploadedConfig(nextSource, apiData.slice(0), ocrData));
      setContentKey((k) => k + 1);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '解析失败');
    } finally {
      setStage(null);
    }
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      <input
        ref={fileInputRef}
        type="file"
        accept={SOURCE_ACCEPT}
        hidden
        disabled={parsing}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void processFile(file);
          e.target.value = '';
        }}
      />

      <ResizablePanelGroup direction="horizontal" className="min-h-0 flex-1">
        <ResizablePanel defaultSize={50} minSize={28} className="min-w-0">
          <div className="flex h-full min-h-0 flex-col bg-card">
            <PanelToolbar title="原文">
              <Button
                size="sm"
                disabled={parsing}
                title={
                  preview ? '选择其他文件并重新解析' : '选择 PDF 或图片进行解析'
                }
                onClick={() => !parsing && fileInputRef.current?.click()}
              >
                <IconSwap
                  state={parsing ? 'b' : 'a'}
                  iconA={<ScanText />}
                  iconB={<Loader2 className="animate-spin" />}
                />
                解析文档
              </Button>
            </PanelToolbar>

            <div className="relative min-h-0 flex-1">
              {!preview ? (
                <SourceDropzone
                  busy={parsing}
                  busyLabel={stage ? STAGE_LABEL[stage] : undefined}
                  onFile={(file) => void processFile(file)}
                />
              ) : (
                <div className="absolute inset-0">
                  {preview.kind === 'image' ? (
                    <ImageViewer
                      imageData={preview.data}
                      mimeType={preview.mimeType}
                      elements={parsedReady ? data.elements : []}
                      activeId={activeId}
                      onHover={setHover}
                      onActivate={handleActivate}
                      scrollRef={pdfScrollRef}
                      onScroll={handlePdfScroll}
                    />
                  ) : (
                    <PdfViewer
                      pdfData={preview.data}
                      pageCount={parsedReady ? data.pageCount : 0}
                      elements={parsedReady ? data.elements : []}
                      activeId={activeId}
                      onHover={setHover}
                      onActivate={handleActivate}
                      scrollRef={pdfScrollRef}
                      onScroll={handlePdfScroll}
                    />
                  )}
                </div>
              )}

              {parsing && preview && (
                <div className="absolute inset-0 z-10 flex items-center justify-center bg-card/75 backdrop-blur-[1px]">
                  <Spinner
                    label={stage ? STAGE_LABEL[stage] : undefined}
                  />
                </div>
              )}
            </div>
          </div>
        </ResizablePanel>

        <ResizableHandle withHandle className="panel-divider" />

        <ResizablePanel defaultSize={50} minSize={28} className="min-w-0">
          <div className="flex h-full min-h-0 flex-col bg-card">
            <PanelToolbar title="Markdown">
              <span className="shrink-0 text-xs text-toolbar-muted">
                {parsing
                  ? '解析中…'
                  : parsedReady
                    ? `${data.pageCount} 页 · ${data.elements.length} 个元素`
                    : ''}
              </span>
            </PanelToolbar>

            <div className="min-h-0 flex-1">
              <MarkdownResultPanel
                parsing={parsing}
                ready={parsedReady}
                blocks={parsedReady ? data.blocks : null}
                contentKey={contentKey}
                activeId={activeId}
                onHover={setHover}
                onActivate={handleActivate}
                scrollRef={mdScrollRef}
                onScroll={handleMdScroll}
              />
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
}
