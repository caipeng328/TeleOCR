export type ElementType =
  | 'title'
  | 'text'
  | 'header'
  | 'image'
  | 'table'
  | 'ref_text'
  | 'inline_equation'
  | 'interline_equation';

export interface Span {
  bbox: [number, number, number, number];
  type: string;
  content?: string;
  score?: number;
  image_path?: string;
  /** 接口返回的图片 base64 / data URL */
  image_url?: string;
  html?: string;
}

export interface Line {
  bbox: [number, number, number, number];
  spans: Span[];
}

export interface NestedBlock {
  bbox: [number, number, number, number];
  type: string;
  index: number;
  angle: number;
  lines: Line[];
}

export interface Block {
  bbox: [number, number, number, number];
  type: string;
  angle: number;
  index: number;
  lines?: Line[];
  level?: number;
  merge_prev?: boolean;
  blocks?: NestedBlock[];
}

export interface PageInfo {
  preproc_blocks?: Block[];
  discarded_blocks: Block[];
  page_size: [number, number];
  page_idx: number;
  para_blocks: Block[];
}

export interface PdfOcrData {
  pdf_info: PageInfo[];
  _backend?: string;
  _version_name?: string;
}

/** 带页码的块，用于 Markdown 渲染 */
export interface BlockWithPage extends Block {
  pageIdx: number;
  pageSize: [number, number];
}

/** 可高亮的元素，PDF 与 Markdown 共用同一 id */
export interface HighlightElement {
  id: string;
  blockIndex: number;
  spanIndex?: number;
  type: ElementType;
  bbox: [number, number, number, number];
  content: string;
  pageIdx: number;
  pageSize: [number, number];
}

export interface ParsedOcrDocument {
  elements: HighlightElement[];
  blocks: BlockWithPage[];
  pageCount: number;
}

/** 一份待展示的文档：原文数据 + 对应的 OCR 结果 */
export interface DocumentConfig {
  id: string;
  title: string;
  description: string;
  pdfData?: ArrayBuffer;
  imageData?: ArrayBuffer;
  imageMimeType?: string;
  ocrData: PdfOcrData;
}
