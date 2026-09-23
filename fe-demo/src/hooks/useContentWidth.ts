import { useEffect, useRef, useState, type RefObject } from 'react';

/**
 * 观察滚动容器的内容宽度（已扣掉左右 padding），用于给 PDF 页面 / 图片定宽。
 * 量不到时返回 0，调用方据此决定是否渲染内容。
 */
export function useContentWidth(ref: RefObject<HTMLElement | null>): number {
  const [width, setWidth] = useState(0);
  const rafRef = useRef(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const measure = () => {
      const style = getComputedStyle(el);
      const padX =
        parseFloat(style.paddingLeft || '0') +
        parseFloat(style.paddingRight || '0');
      const next = Math.floor(el.clientWidth - padX);
      if (next <= 0) return;
      setWidth((prev) => (Math.abs(prev - next) >= 1 ? next : prev));
    };

    measure();

    // ResizeObserver 会连续触发，用 rAF 合并到一帧
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(measure);
    });
    observer.observe(el);

    return () => {
      cancelAnimationFrame(rafRef.current);
      observer.disconnect();
    };
  }, [ref]);

  return width;
}
