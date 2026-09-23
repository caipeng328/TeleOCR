import type { Block, Line, NestedBlock, PageInfo, PdfOcrData, Span } from '../types';

/** 推理接口嵌套子块（image_body / image_caption / table_body 等） */
interface InferNestedBlock {
  type: string;
  angle?: number;
  index?: number;
  pos: [number, number, number, number];
  text?: string;
  content?: string;
  image_url?: string;
  html?: string;
}

/** 推理接口 content 块 */
interface InferContentItem {
  type: string;
  angle: number;
  index: number;
  pos: [number, number, number, number];
  text?: string;
  content?: string;
  /** 图片块：顶层也可能直接带 base64（兼容） */
  image_url?: string;
  html?: string;
  blocks?: InferNestedBlock[];
}

/** 推理接口单页 */
interface InferPage {
  page_id: number;
  width: number;
  height: number;
  content: InferContentItem[];
  discarded_blocks?: InferContentItem[];
}

/** words_result[0] 解析结果 */
interface InferWordsResult {
  pages: InferPage[];
  total_page_number?: number;
  markdown?: string;
}

/** 推理接口顶层响应 */
interface InferApiResponse {
  code: string;
  flag?: number;
  message?: string;
  seqid?: string;
  data?: {
    timeSecond?: number;
    words_result?: string[];
  };
}

function isInferApiResponse(value: unknown): value is InferApiResponse {
  if (typeof value !== 'object' || value === null) return false;
  const record = value as Record<string, unknown>;
  return (
    'code' in record &&
    typeof record.data === 'object' &&
    record.data !== null &&
    'words_result' in (record.data as object)
  );
}

/** 将含 $...$ 的文本拆成 text / inline_equation spans */
function parseInlineSpans(text: string, bbox: [number, number, number, number]): Span[] {
  if (!text.includes('$')) {
    return [{ bbox, type: 'text', content: text, score: 1 }];
  }

  const spans: Span[] = [];
  const regex = /\$([^$]+)\$/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      spans.push({
        bbox,
        type: 'text',
        content: text.slice(lastIndex, match.index),
        score: 1,
      });
    }
    spans.push({
      bbox,
      type: 'inline_equation',
      content: match[1],
      score: 1,
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    spans.push({ bbox, type: 'text', content: text.slice(lastIndex), score: 1 });
  }

  return spans.length > 0 ? spans : [{ bbox, type: 'text', content: text, score: 1 }];
}

function nestedText(item: InferNestedBlock | InferContentItem): string {
  return item.text ?? item.content ?? '';
}

function convertNestedBlock(item: InferNestedBlock, fallbackIndex: number): NestedBlock {
  const bbox = item.pos;
  const nested: NestedBlock = {
    bbox,
    type: item.type,
    index: item.index ?? fallbackIndex,
    angle: item.angle ?? 0,
    lines: [],
  };

  if (item.type === 'image_body' || item.image_url) {
    nested.lines = [
      {
        bbox,
        spans: [
          {
            bbox,
            type: 'image',
            content: nestedText(item),
            image_url: item.image_url,
            score: 1,
          },
        ],
      },
    ];
    return nested;
  }

  if (item.type === 'table_body' || item.html) {
    nested.lines = [
      {
        bbox,
        spans: [
          {
            bbox,
            type: 'table',
            content: nestedText(item),
            html: item.html,
            score: 1,
          },
        ],
      },
    ];
    return nested;
  }

  nested.lines = [{ bbox, spans: parseInlineSpans(nestedText(item), bbox) }];
  return nested;
}

function buildLines(item: InferContentItem): Line[] {
  const bbox = item.pos;
  const text = nestedText(item);

  if (item.type === 'interline_equation') {
    return [
      {
        bbox,
        spans: [{ bbox, type: 'interline_equation', content: text, score: 1 }],
      },
    ];
  }

  if (item.type === 'image' && item.image_url) {
    return [
      {
        bbox,
        spans: [
          {
            bbox,
            type: 'image',
            content: text,
            image_url: item.image_url,
            score: 1,
          },
        ],
      },
    ];
  }

  if (item.type === 'table' && item.html) {
    return [
      {
        bbox,
        spans: [
          {
            bbox,
            type: 'table',
            content: text,
            html: item.html,
            score: 1,
          },
        ],
      },
    ];
  }

  if (!text) return [];
  return [{ bbox, spans: parseInlineSpans(text, bbox) }];
}

function inferTitleLevel(titleIndexOnPage: number, item: InferContentItem): number {
  if (titleIndexOnPage === 0) return 1;
  const height = item.pos[3] - item.pos[1];
  if (height >= 20) return 2;
  return 3;
}

function convertContentItem(
  item: InferContentItem,
  titleIndexOnPage: number,
): Block {
  const block: Block = {
    bbox: item.pos,
    type: item.type,
    angle: item.angle ?? 0,
    index: item.index,
    lines: buildLines(item),
  };

  if (item.blocks?.length) {
    block.blocks = item.blocks.map((nested, i) => convertNestedBlock(nested, i));
  }

  if (item.type === 'title') {
    block.level = inferTitleLevel(titleIndexOnPage, item);
  }

  return block;
}

function convertPage(page: InferPage): PageInfo {
  let titleCount = 0;
  const para_blocks = (page.content ?? []).map((item) => {
    const titleIndex = item.type === 'title' ? titleCount : 0;
    const block = convertContentItem(item, titleIndex);
    if (item.type === 'title') titleCount += 1;
    return block;
  });

  const discarded_blocks = (page.discarded_blocks ?? []).map((item, i) =>
    convertContentItem({ ...item, index: item.index ?? i }, 0),
  );

  return {
    page_idx: page.page_id,
    page_size: [page.width, page.height],
    para_blocks,
    discarded_blocks,
    preproc_blocks: para_blocks,
  };
}

function parseWordsResult(raw: string): InferWordsResult {
  try {
    return JSON.parse(raw) as InferWordsResult;
  } catch {
    throw new Error('words_result 不是合法的 JSON 字符串');
  }
}

/** 将推理接口响应转为 MinerU 兼容的 PdfOcrData */
function convertInferApiToPdfOcrData(payload: InferApiResponse): PdfOcrData {
  if (payload.code !== '10000') {
    throw new Error(payload.message || `OCR 接口错误 (code=${payload.code})`);
  }

  const wordsResult = payload.data?.words_result;
  if (!wordsResult?.length) {
    throw new Error('接口响应缺少 words_result');
  }

  const allPages: InferPage[] = [];
  for (const raw of wordsResult) {
    const parsed = parseWordsResult(raw);
    if (parsed.pages?.length) {
      allPages.push(...parsed.pages);
    }
  }

  if (allPages.length === 0) {
    throw new Error('words_result 中未找到 pages 数据');
  }

  allPages.sort((a, b) => a.page_id - b.page_id);

  return {
    pdf_info: allPages.map(convertPage),
    _backend: 'infer-api',
    _version_name: '1.0',
  };
}

export function tryConvertInferApiResponse(payload: unknown): PdfOcrData | null {
  if (!isInferApiResponse(payload)) return null;
  return convertInferApiToPdfOcrData(payload);
}
