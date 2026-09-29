import { useEffect, useState, type RefObject } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { FileText } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';
import { MarkdownViewer } from '@/components/MarkdownViewer';
import type { BlockWithPage } from '@/types';

type RevealPhase = 'empty' | 'loading' | 'revealing' | 'ready';

interface MarkdownResultPanelProps {
  /** 首次/重新解析中：展示骨架屏 */
  parsing: boolean;
  ready: boolean;
  blocks: BlockWithPage[] | null;
  /** 内容更新时递增，触发内容渐显过渡 */
  contentKey?: number;
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
}

function MarkdownSkeleton() {
  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden bg-card p-6">
      <Skeleton className="h-7 w-2/3" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-[92%]" />
      <Skeleton className="h-4 w-[85%]" />
      <div className="mt-2 space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-[96%]" />
        <Skeleton className="h-4 w-[78%]" />
      </div>
      <Skeleton className="mt-4 h-28 w-full rounded-xl" />
      <div className="space-y-3">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-[88%]" />
        <Skeleton className="h-4 w-[94%]" />
        <Skeleton className="h-4 w-[70%]" />
      </div>
      <div className="mt-2 flex gap-3">
        <Skeleton className="h-16 flex-1 rounded-lg" />
        <Skeleton className="h-16 flex-1 rounded-lg" />
      </div>
      <Skeleton className="h-4 w-[82%]" />
      <Skeleton className="h-4 w-[90%]" />
    </div>
  );
}

/**
 * 右侧结果区：
 * - 解析中 → Skeleton → Markdown 渐显
 * - contentKey 变化时触发内容隐显过渡
 */
export function MarkdownResultPanel({
  parsing,
  ready,
  blocks,
  contentKey = 0,
  activeId,
  onHover,
  onActivate,
  scrollRef,
  onScroll,
}: MarkdownResultPanelProps) {
  const [phase, setPhase] = useState<RevealPhase>('empty');

  useEffect(() => {
    if (parsing) {
      setPhase('loading');
      return;
    }
    if (ready && blocks) {
      setPhase((prev) => (prev === 'loading' ? 'revealing' : 'ready'));
      return;
    }
    setPhase('empty');
  }, [parsing, ready, blocks]);

  useEffect(() => {
    if (phase !== 'revealing') return;
    const timer = window.setTimeout(() => setPhase('ready'), 650);
    return () => window.clearTimeout(timer);
  }, [phase]);

  const showContent = (phase === 'revealing' || phase === 'ready') && blocks;
  const contentMotionKey = `md-${contentKey}`;

  return (
    <div className="relative h-full min-h-0 overflow-hidden bg-card">
      <AnimatePresence mode="sync">
        {phase === 'empty' && (
          <motion.div
            key="empty"
            className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-8 text-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <div className="flex size-14 items-center justify-center rounded-2xl bg-secondary">
              <FileText className="size-6 text-primary-ink" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">解析结果将显示在这里</p>
              <p className="text-xs text-muted-foreground">
                点击左侧「解析文档」或拖拽文件到左侧，选择后将自动开始 OCR
              </p>
            </div>
          </motion.div>
        )}

        {(phase === 'loading' || phase === 'revealing') && (
          <motion.div
            key="skeleton"
            className="absolute inset-0 z-[1]"
            initial={{ opacity: 1 }}
            animate={{ opacity: phase === 'revealing' ? 0 : 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.45, ease: 'easeOut' }}
          >
            <MarkdownSkeleton />
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence mode="wait">
        {showContent ? (
          <motion.div
            key={contentMotionKey}
            className="absolute inset-0 z-[2]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4, ease: 'easeOut' }}
          >
            <MarkdownViewer
              blocks={blocks}
              activeId={activeId}
              onHover={onHover}
              onActivate={onActivate}
              scrollRef={scrollRef}
              onScroll={onScroll}
            />
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
