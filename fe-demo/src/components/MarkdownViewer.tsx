import { Fragment, useCallback, type RefObject } from 'react';
import type { BlockWithPage, NestedBlock, Span } from '../types';
import { makeElementId, makeNestedItemId } from '../utils/elementId';
import {
  getBlockContent,
  getNestedCaption,
  getNestedImagePath,
  getNestedTableHtml,
  groupByPage,
  toDisplayImageSrc,
} from '../utils/parseElements';
import { renderLatex, renderTextWithMath } from '../utils/renderLatex';

interface HighlightableProps {
  id: string;
  activeId: string | null;
  className?: string;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
  children: React.ReactNode;
}

function Highlightable({
  id,
  activeId,
  className = '',
  onHover,
  onActivate,
  children,
}: HighlightableProps) {
  const isActive = activeId === id;
  const handleEnter = useCallback(() => onHover(id), [id, onHover]);
  const handleLeave = useCallback(() => onHover(null), [onHover]);
  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onActivate(id);
    },
    [id, onActivate],
  );

  return (
    <span
      className={`highlightable ${className} ${isActive ? 'active' : ''}`}
      data-id={id}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      onClick={handleClick}
    >
      {children}
    </span>
  );
}

function RichText({ html }: { html: string }) {
  return <span dangerouslySetInnerHTML={{ __html: renderTextWithMath(html) }} />;
}

interface SpanRendererProps {
  span: Span;
  pageIdx: number;
  blockIndex: number;
  spanIndex: number;
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
}

function SpanRenderer({
  span,
  pageIdx,
  blockIndex,
  spanIndex,
  activeId,
  onHover,
  onActivate,
}: SpanRendererProps) {
  const id = makeElementId(pageIdx, blockIndex, spanIndex);
  const isMath = span.type === 'inline_equation';

  return (
    <Highlightable
      id={id}
      activeId={activeId}
      onHover={onHover}
      onActivate={onActivate}
      className={isMath ? 'md-math-inline' : undefined}
    >
      {isMath ? (
        <span
          dangerouslySetInnerHTML={{
            __html: renderLatex(span.content ?? '', false),
          }}
        />
      ) : (
        <RichText html={span.content ?? ''} />
      )}
    </Highlightable>
  );
}

interface NestedItemRendererProps {
  nested: NestedBlock;
  pageIdx: number;
  parentIndex: number;
  itemIndex: number;
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
}

function NestedItemRenderer({
  nested,
  pageIdx,
  parentIndex,
  itemIndex,
  activeId,
  onHover,
  onActivate,
}: NestedItemRendererProps) {
  const id = makeNestedItemId(pageIdx, parentIndex, itemIndex);

  if (nested.type === 'ref_text' || nested.type === 'text') {
    return (
      <Highlightable
        id={id}
        activeId={activeId}
        onHover={onHover}
        onActivate={onActivate}
        className={nested.type === 'ref_text' ? 'md-ref' : 'md-text'}
      >
        <p>
          <RichText html={getBlockContent(nested)} />
        </p>
      </Highlightable>
    );
  }

  return null;
}

interface BlockRendererProps {
  block: BlockWithPage;
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
}

function BlockRenderer({ block, activeId, onHover, onActivate }: BlockRendererProps) {
  const spans = block.lines?.flatMap((line) => line.spans) ?? [];
  // 每个分支都要把这几个 prop 原样透传给 Highlightable，收成一个对象免得刷屏
  const hl = {
    id: makeElementId(block.pageIdx, block.index),
    activeId,
    onHover,
    onActivate,
  };

  switch (block.type) {
    case 'title': {
      const level = block.level ?? 2;
      const Tag = level === 1 ? 'h1' : level === 2 ? 'h2' : 'h3';
      return (
        <Highlightable {...hl} className={`md-title md-h${level}`}>
          <Tag>
            <RichText html={getBlockContent(block)} />
          </Tag>
        </Highlightable>
      );
    }

    case 'header':
      return (
        <Highlightable {...hl} className="md-header">
          <p>
            <RichText html={getBlockContent(block)} />
          </p>
        </Highlightable>
      );

    case 'ref_text':
      return (
        <Highlightable {...hl} className="md-ref">
          <p>
            <RichText html={getBlockContent(block)} />
          </p>
        </Highlightable>
      );

    case 'list':
      return (
        <div className="md-list">
          {block.blocks?.map((nested, itemIndex) => (
            <NestedItemRenderer
              key={itemIndex}
              nested={nested}
              pageIdx={block.pageIdx}
              parentIndex={block.index}
              itemIndex={itemIndex}
              activeId={activeId}
              onHover={onHover}
              onActivate={onActivate}
            />
          ))}
        </div>
      );

    case 'interline_equation':
      return (
        <Highlightable {...hl} className="md-math-block">
          <div
            dangerouslySetInnerHTML={{
              __html: renderLatex(spans[0]?.content ?? '', true),
            }}
          />
        </Highlightable>
      );

    case 'image': {
      const imageRaw = getNestedImagePath(block);
      const imageSrc = imageRaw ? toDisplayImageSrc(imageRaw) : null;
      const caption = getNestedCaption(block) || getBlockContent(block);
      return (
        <Highlightable {...hl} className="md-image-block">
          <figure>
            {imageSrc ? (
              <img
                src={imageSrc}
                alt={caption ? caption.replace(/<[^>]+>/g, '') : 'Figure'}
                className="md-image"
                loading="lazy"
              />
            ) : (
              <div className="md-image-placeholder">[Image]</div>
            )}
            {caption && (
              <figcaption>
                <RichText html={caption} />
              </figcaption>
            )}
          </figure>
        </Highlightable>
      );
    }

    case 'table': {
      const html = getNestedTableHtml(block);
      const caption = getNestedCaption(block);
      return (
        <Highlightable {...hl} className="md-table-block">
          {html ? (
            <div className="md-table" dangerouslySetInnerHTML={{ __html: html }} />
          ) : (
            <div className="md-table-placeholder">[Table]</div>
          )}
          {caption && (
            <p className="md-caption">
              <RichText html={caption} />
            </p>
          )}
        </Highlightable>
      );
    }

    case 'text': {
      // 与 parseElements 的切分保持一致：不含行内公式时整段是一个高亮单元，
      // 含公式时拆到 span 粒度，公式本身才能单独高亮
      const hasInlineEq = spans.some((s) => s.type === 'inline_equation');

      if (!hasInlineEq) {
        return (
          <Highlightable {...hl} className="md-text">
            <p>
              <RichText html={getBlockContent(block)} />
            </p>
          </Highlightable>
        );
      }

      return (
        <p className="md-text md-inline-paragraph">
          {spans.map((span, i) => (
            <Fragment key={i}>
              {i > 0 && ' '}
              <SpanRenderer
                span={span}
                pageIdx={block.pageIdx}
                blockIndex={block.index}
                spanIndex={i}
                activeId={activeId}
                onHover={onHover}
                onActivate={onActivate}
              />
            </Fragment>
          ))}
        </p>
      );
    }

    default:
      return null;
  }
}

interface MarkdownViewerProps {
  blocks: BlockWithPage[];
  activeId: string | null;
  onHover: (id: string | null) => void;
  onActivate: (id: string) => void;
  scrollRef: RefObject<HTMLDivElement | null>;
  onScroll: () => void;
}

/** 从 OCR para_blocks 动态渲染 Markdown 视图 */
export function MarkdownViewer({
  blocks,
  activeId,
  onHover,
  onActivate,
  scrollRef,
  onScroll,
}: MarkdownViewerProps) {
  const blocksByPage = groupByPage(blocks);
  const pageIndices = [...blocksByPage.keys()].sort((a, b) => a - b);

  return (
    <div className="flex h-full min-h-0 flex-1 flex-col overflow-hidden bg-card">
      <div
        className="markdown-body min-h-0 flex-1 overflow-auto p-4"
        ref={scrollRef}
        onScroll={onScroll}
      >
        {pageIndices.map((pageIdx) => (
          <section
            key={pageIdx}
            className="md-page-section"
            data-page={pageIdx}
          >
            {pageIndices.length > 1 && (
              <div className="md-page-label">Page {pageIdx + 1}</div>
            )}
            {(blocksByPage.get(pageIdx) ?? []).map((block) => (
              <BlockRenderer
                key={`p${pageIdx}-${block.index}-${block.type}`}
                block={block}
                activeId={activeId}
                onHover={onHover}
                onActivate={onActivate}
              />
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
