import { useMemo } from 'react';
import type { DocumentConfig, ParsedOcrDocument } from '../types';
import { parseOcrDocument } from '../utils/parseElements';

interface OcrDocumentState {
  data: ParsedOcrDocument | null;
  error: string | null;
}

/**
 * 把 config 里的原始 OCR JSON 解析成可渲染结构。
 * 解析是同步的，所以没有 loading 态；字段畸形时转成错误信息而不是抛到渲染里。
 */
export function useOcrDocument(config: DocumentConfig | null): OcrDocumentState {
  return useMemo(() => {
    if (!config) return { data: null, error: null };

    try {
      return { data: parseOcrDocument(config.ocrData), error: null };
    } catch (err) {
      return {
        data: null,
        error: err instanceof Error ? err.message : 'OCR 结果解析失败',
      };
    }
  }, [config]);
}
