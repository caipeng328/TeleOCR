import { inferApiUrl } from '../../ocr.config';
import type { PdfOcrData } from '../types';
import { arrayBufferToBase64 } from '../utils/base64';
import { tryConvertInferApiResponse } from './convertInferResponse';

function isPdfOcrData(value: unknown): value is PdfOcrData {
  return (
    typeof value === 'object' &&
    value !== null &&
    'pdf_info' in value &&
    Array.isArray((value as PdfOcrData).pdf_info)
  );
}

/** 从接口响应中提取 OCR JSON（支持推理接口与 MinerU 格式） */
function parseOcrApiResponse(payload: unknown): PdfOcrData {
  const inferData = tryConvertInferApiResponse(payload);
  if (inferData) return inferData;

  const direct = findPdfOcrData(payload);
  if (direct) return direct;

  throw new Error('无法解析 OCR 响应，请确认接口返回格式');
}

function findPdfOcrData(value: unknown, depth = 0): PdfOcrData | null {
  if (depth > 6) return null;
  if (isPdfOcrData(value)) return value;
  if (typeof value !== 'object' || value === null) return null;

  const record = value as Record<string, unknown>;
  for (const key of ['data', 'result', 'ocr', 'output', 'payload', 'body']) {
    const found = findPdfOcrData(record[key], depth + 1);
    if (found) return found;
  }
  return null;
}

/** 1 = PDF，2 = 图片 */
export type InferImageType = 1 | 2;

/** 一次请求经历的阶段，用于驱动进度提示 */
export type InferStage = 'encoding' | 'uploading' | 'parsing';

export interface InferOcrOptions {
  signal?: AbortSignal;
  imageType?: InferImageType;
  onProgress?: (stage: InferStage) => void;
}

interface ApiEnvelope {
  code?: string;
  message?: string;
  data?: {
    timeSecond?: number;
    words_result?: unknown;
  };
}

async function postBinaryApi(
  data: ArrayBuffer,
  options: InferOcrOptions,
): Promise<unknown> {
  const { signal, onProgress, imageType = 1 } = options;

  onProgress?.('encoding');
  const image = arrayBufferToBase64(data);

  onProgress?.('uploading');
  const response = await fetch(inferApiUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal,
    body: JSON.stringify({
      base64: true,
      image,
      image_type: imageType,
    }),
  });

  const text = await response.text();
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const envelope =
      payload && typeof payload === 'object'
        ? (payload as ApiEnvelope)
        : null;
    throw new Error(
      envelope?.message ||
        `接口请求失败 (${response.status})${text.startsWith('<') ? '' : `: ${text.slice(0, 300)}`}`,
    );
  }

  onProgress?.('parsing');
  if (payload == null) {
    throw new Error(`接口返回非 JSON 格式: ${text.slice(0, 200)}`);
  }
  return payload;
}

/** 将文件转为 base64 并调用 OCR 推理接口 */
export async function inferOcr(
  data: ArrayBuffer,
  options: InferOcrOptions = {},
): Promise<PdfOcrData> {
  const payload = await postBinaryApi(data, options);
  return parseOcrApiResponse(payload);
}
