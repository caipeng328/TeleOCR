import { useCallback, useEffect, useRef } from 'react';

const CLEAR_DELAY_MS = 50;

/**
 * 管理跨面板 hover 状态，延迟清除以避免相邻元素间快速触发 leave/enter 导致闪动。
 */
export function useHoverSync() {
  const activeIdRef = useRef<string | null>(null);
  const clearTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const setActiveIdRef = useRef<(id: string | null) => void>(() => {});

  const registerSetter = useCallback((setter: (id: string | null) => void) => {
    setActiveIdRef.current = setter;
  }, []);

  const setHover = useCallback((id: string | null) => {
    if (clearTimerRef.current) {
      clearTimeout(clearTimerRef.current);
      clearTimerRef.current = undefined;
    }

    if (id !== null) {
      activeIdRef.current = id;
      setActiveIdRef.current(id);
      return;
    }

    clearTimerRef.current = setTimeout(() => {
      activeIdRef.current = null;
      setActiveIdRef.current(null);
    }, CLEAR_DELAY_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (clearTimerRef.current) clearTimeout(clearTimerRef.current);
    };
  }, []);

  return { setHover, registerSetter };
}
