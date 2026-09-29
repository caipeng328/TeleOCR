import katex from 'katex';

/** 去掉 OCR 输出的 $ / $$ 包裹及行尾公式编号 */
function normalizeLatex(raw: string): string {
  let s = raw.trim();
  s = s.replace(/\s*\(\d+\)\s*$/, '');
  if (s.startsWith('$$') && s.endsWith('$$')) {
    return s.slice(2, -2).trim();
  }
  if (s.startsWith('$') && s.endsWith('$') && s.length > 1) {
    return s.slice(1, -1).trim();
  }
  return s;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function renderLatex(latex: string, displayMode: boolean): string {
  const normalized = normalizeLatex(latex);
  if (!normalized) return '';

  try {
    return katex.renderToString(normalized, {
      displayMode,
      throwOnError: false,
      strict: false,
    });
  } catch {
    return escapeHtml(latex);
  }
}

/**
 * 渲染混合文本：识别 $...$ / $$...$$ 中的 LaTeX 并用 KaTeX 输出。
 * OCR 文本块中的公式通常以 $ 分隔，而非 inline_equation span。
 */
export function renderTextWithMath(text: string): string {
  if (!text) return '';

  const regex = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;
  const parts: string[] = [];
  let lastIndex = 0;

  for (const match of text.matchAll(regex)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      parts.push(escapeHtml(text.slice(lastIndex, index)));
    }
    const token = match[0];
    const isDisplay = token.startsWith('$$');
    parts.push(renderLatex(token, isDisplay));
    lastIndex = index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(escapeHtml(text.slice(lastIndex)));
  }

  return parts.join('');
}

