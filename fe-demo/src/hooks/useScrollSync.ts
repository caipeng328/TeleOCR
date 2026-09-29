import { useCallback, useEffect, useRef } from 'react';
import {
  resolveScrollAnchor,
  scrollToAnchor,
  scrollToElementInContainer,
} from '../utils/scrollInContainer';

const SYNC_LOCK_MS = 80;
const DEFAULT_DEBOUNCE_MS = 100;

export function useScrollSync(debounceMs = DEFAULT_DEBOUNCE_MS) {
  const pdfScrollRef = useRef<HTMLDivElement>(null);
  const mdScrollRef = useRef<HTMLDivElement>(null);
  const syncingRef = useRef(false);
  const debounceTimers = useRef<{ pdf?: number; md?: number }>({});

  const lockSync = useCallback((duration = SYNC_LOCK_MS) => {
    syncingRef.current = true;
    window.setTimeout(() => {
      syncingRef.current = false;
    }, duration);
  }, []);

  const scrollToId = useCallback(
    (id: string, behavior: ScrollBehavior = 'smooth') => {
      if (!id) return;

      const pdfContainer = pdfScrollRef.current;
      const mdContainer = mdScrollRef.current;
      const pdfEl = pdfContainer?.querySelector<HTMLElement>(
        `[data-id="${CSS.escape(id)}"]`,
      );
      const mdEl = mdContainer?.querySelector<HTMLElement>(
        `[data-id="${CSS.escape(id)}"]`,
      );

      lockSync(behavior === 'smooth' ? 450 : SYNC_LOCK_MS);

      if (pdfEl && pdfContainer) {
        scrollToElementInContainer(pdfContainer, pdfEl, behavior);
      }
      if (mdEl && mdContainer) {
        scrollToElementInContainer(mdContainer, mdEl, behavior);
      }
    },
    [lockSync],
  );

  const syncPanels = useCallback(
    (source: 'pdf' | 'md', behavior: ScrollBehavior = 'auto') => {
      if (syncingRef.current) return;

      const from =
        source === 'pdf' ? pdfScrollRef.current : mdScrollRef.current;
      const to =
        source === 'pdf' ? mdScrollRef.current : pdfScrollRef.current;
      if (!from || !to) return;

      const anchor = resolveScrollAnchor(from, to);
      if (!anchor) return;

      lockSync();
      scrollToAnchor(to, anchor, behavior);
    },
    [lockSync],
  );

  const handlePdfScroll = useCallback(() => {
    if (syncingRef.current) return;
    clearTimeout(debounceTimers.current.pdf);
    debounceTimers.current.pdf = window.setTimeout(() => {
      syncPanels('pdf');
    }, debounceMs);
  }, [debounceMs, syncPanels]);

  const handleMdScroll = useCallback(() => {
    if (syncingRef.current) return;
    clearTimeout(debounceTimers.current.md);
    debounceTimers.current.md = window.setTimeout(() => {
      syncPanels('md');
    }, debounceMs);
  }, [debounceMs, syncPanels]);

  useEffect(() => {
    return () => {
      clearTimeout(debounceTimers.current.pdf);
      clearTimeout(debounceTimers.current.md);
    };
  }, []);

  return {
    pdfScrollRef,
    mdScrollRef,
    scrollToId,
    handlePdfScroll,
    handleMdScroll,
  };
}
