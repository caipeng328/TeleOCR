import type {
  Block,
  BlockWithPage,
  HighlightElement,
  PdfOcrData,
  ParsedOcrDocument,
  Span,
} from '../types';
import { makeElementId, makeNestedItemId } from './elementId';

export function getBlockContent(block: {
  lines?: { spans: Span[] }[];
  blocks?: { lines: { spans: Span[] }[] }[];
}): string {
  if (block.lines?.length) {
    return block.lines
      .map((line) => line.spans.map((s) => s.content ?? '').join(''))
      .join(' ');
  }
  return '';
}

/** 从嵌套 blocks（image / table）中提取 caption 文本 */
export function getNestedCaption(block: Block): string {
  const caption = block.blocks?.find(
    (b) => b.type === 'image_caption' || b.type === 'table_caption',
  );
  return caption ? getBlockContent(caption) : '';
}

/** 从嵌套 blocks 中提取 table HTML */
export function getNestedTableHtml(block: Block): string {
  for (const nested of block.blocks ?? []) {
    for (const line of nested.lines ?? []) {
      for (const span of line.spans) {
        if (span.html) return span.html;
      }
    }
  }
  return '';
}

function pickSpanImageSrc(span: Span): string | undefined {
  const raw = span.image_url || span.image_path;
  return raw?.trim() ? raw.trim() : undefined;
}

/** 从 image 块中提取原始图片字段（base64 / URL / 路径） */
export function getNestedImagePath(block: Block): string | undefined {
  for (const nested of block.blocks ?? []) {
    for (const line of nested.lines ?? []) {
      for (const span of line.spans) {
        const src = pickSpanImageSrc(span);
        if (src) return src;
      }
    }
  }
  if (block.lines) {
    for (const line of block.lines) {
      for (const span of line.spans) {
        const src = pickSpanImageSrc(span);
        if (src) return src;
      }
    }
  }
  return undefined;
}

function guessMimeFromBase64(b64: string): string {
  if (b64.startsWith('/9j/')) return 'image/jpeg';
  if (b64.startsWith('iVBOR')) return 'image/png';
  if (b64.startsWith('R0lGOD')) return 'image/gif';
  if (b64.startsWith('UklGR')) return 'image/webp';
  return 'image/jpeg';
}

/**
 * 将接口返回的 image_url / image_path 转为可给 <img src> 使用的地址。
 * 支持 data URL、http(s)、以及裸 base64。
 */
export function toDisplayImageSrc(raw: string): string | null {
  const value = raw.replace(/\s+/g, '');
  if (!value) return null;

  if (
    value.startsWith('data:') ||
    value.startsWith('http://') ||
    value.startsWith('https://') ||
    value.startsWith('blob:')
  ) {
    return value;
  }

  // 旧 demo 相对路径（如 image/xxx.jpeg）无法直接展示
  if (/\.(jpe?g|png|gif|webp|bmp)$/i.test(value) && value.includes('/')) {
    return null;
  }

  const mime = guessMimeFromBase64(value);
  return `data:${mime};base64,${value}`;
}

export function parseOcrDocument(data: PdfOcrData): ParsedOcrDocument {
  return {
    elements: extractHighlightElements(data),
    blocks: getOrderedBlocks(data),
    pageCount: data.pdf_info.length,
  };
}

/** 按页码排序，取出所有 para_blocks 并附加页信息 */
function getOrderedBlocks(data: PdfOcrData): BlockWithPage[] {
  return [...data.pdf_info]
    .sort((a, b) => a.page_idx - b.page_idx)
    .flatMap((page) =>
      (page.para_blocks as Block[]).map((block) => ({
        ...block,
        pageIdx: page.page_idx,
        pageSize: page.page_size,
      })),
    );
}

const NESTED_HIGHLIGHTABLE = new Set(['ref_text', 'text']);

const HIGHLIGHTABLE_TYPES = new Set([
  'title',
  'text',
  'header',
  'image',
  'table',
  'ref_text',
  'interline_equation',
  'list',
]);

function extractBlockElement(
  elements: HighlightElement[],
  block: Block,
  pageIdx: number,
  pageSize: [number, number],
  id: string,
) {
  const spans = block.lines?.flatMap((line) => line.spans) ?? [];
  const common = { blockIndex: block.index, pageIdx, pageSize };

  switch (block.type) {
    case 'text':
    case 'ref_text': {
      // 含行内公式的段落拆到 span 粒度，这样公式本身也能单独高亮
      const hasInlineEq = spans.some((s) => s.type === 'inline_equation');
      if (hasInlineEq) {
        spans.forEach((span, i) => {
          elements.push({
            ...common,
            id: `${id}-span-${i}`,
            spanIndex: i,
            type: span.type as HighlightElement['type'],
            bbox: span.bbox,
            content: span.content ?? '',
          });
        });
        return;
      }
      elements.push({
        ...common,
        id,
        type: block.type,
        bbox: block.bbox,
        content: getBlockContent(block),
      });
      return;
    }

    case 'title':
    case 'header':
      elements.push({
        ...common,
        id,
        type: block.type,
        bbox: block.bbox,
        content: getBlockContent(block),
      });
      return;

    case 'interline_equation':
      elements.push({
        ...common,
        id,
        type: 'interline_equation',
        bbox: block.bbox,
        content: spans[0]?.content ?? '',
      });
      return;

    case 'image':
    case 'table':
      elements.push({
        ...common,
        id,
        type: block.type,
        bbox: block.bbox,
        content: getBlockContent(block) || getNestedCaption(block),
      });
      return;
  }
}

/**
 * 从 MinerU OCR 的 para_blocks 提取可高亮元素。
 * ID 格式：p{pageIdx}-{blockIndex} 或 p{pageIdx}-{parentIndex}-item-{i}
 */
function extractHighlightElements(data: PdfOcrData): HighlightElement[] {
  const elements: HighlightElement[] = [];

  for (const page of data.pdf_info) {
    const { page_idx: pageIdx, page_size: pageSize, para_blocks } = page;

    for (const block of para_blocks as Block[]) {
      if (!HIGHLIGHTABLE_TYPES.has(block.type)) continue;

      if (block.type === 'list') {
        block.blocks?.forEach((nested, itemIndex) => {
          if (!NESTED_HIGHLIGHTABLE.has(nested.type)) return;
          extractBlockElement(
            elements,
            nested,
            pageIdx,
            pageSize,
            makeNestedItemId(pageIdx, block.index, itemIndex),
          );
        });
        continue;
      }

      extractBlockElement(
        elements,
        block,
        pageIdx,
        pageSize,
        makeElementId(pageIdx, block.index),
      );
    }
  }

  return elements;
}

/** 将 OCR bbox [x0,y0,x1,y1] 转为 CSS 百分比定位 */
export function bboxToPercent(
  bbox: [number, number, number, number],
  pageSize: [number, number],
) {
  const [pageW, pageH] = pageSize;
  const [x0, y0, x1, y1] = bbox;
  return {
    left: `${(x0 / pageW) * 100}%`,
    top: `${(y0 / pageH) * 100}%`,
    width: `${((x1 - x0) / pageW) * 100}%`,
    height: `${((y1 - y0) / pageH) * 100}%`,
  };
}

/** 按页码把带 pageIdx 的元素或块分组 */
export function groupByPage<T extends { pageIdx: number }>(
  items: T[],
): Map<number, T[]> {
  const byPage = new Map<number, T[]>();
  for (const item of items) {
    const list = byPage.get(item.pageIdx);
    if (list) list.push(item);
    else byPage.set(item.pageIdx, [item]);
  }
  return byPage;
}
