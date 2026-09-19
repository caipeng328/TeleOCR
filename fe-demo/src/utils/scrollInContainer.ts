/** 在可滚动容器内将元素滚入视口 */
export function scrollToElementInContainer(
  container: HTMLElement,
  element: HTMLElement,
  behavior: ScrollBehavior = 'auto',
  align: 'center' | 'start' = 'center',
) {
  const containerRect = container.getBoundingClientRect();
  const elRect = element.getBoundingClientRect();
  const elTop = elRect.top - containerRect.top + container.scrollTop;

  let target: number;
  if (align === 'center') {
    target = elTop - container.clientHeight / 2 + elRect.height / 2;
  } else {
    target = elTop - 24;
  }

  container.scrollTo({
    top: Math.max(0, target),
    behavior,
  });
}

function queryById(container: HTMLElement, id: string): HTMLElement | null {
  return container.querySelector<HTMLElement>(`[data-id="${CSS.escape(id)}"]`);
}

/** 找到视口中心附近最近的锚点元素 id */
function findClosestAnchorId(container: HTMLElement): string | null {
  const anchors = container.querySelectorAll<HTMLElement>('[data-id]');
  if (anchors.length === 0) return null;

  const containerRect = container.getBoundingClientRect();
  const viewportCenter = containerRect.top + containerRect.height / 2;

  let bestId: string | null = null;
  let bestDist = Infinity;

  for (const el of anchors) {
    const rect = el.getBoundingClientRect();
    if (rect.bottom < containerRect.top || rect.top > containerRect.bottom) continue;

    const center = rect.top + rect.height / 2;
    const dist = Math.abs(center - viewportCenter);
    if (dist < bestDist) {
      bestDist = dist;
      bestId = el.dataset.id ?? null;
    }
  }

  return bestId;
}

/** 找到当前视口内可见面积最大的页码 */
function findVisiblePageIdx(container: HTMLElement): number | null {
  const pages = container.querySelectorAll<HTMLElement>('[data-page]');
  if (pages.length === 0) return null;

  const containerRect = container.getBoundingClientRect();
  let bestPage: number | null = null;
  let bestVisible = 0;

  for (const page of pages) {
    const rect = page.getBoundingClientRect();
    const visible =
      Math.min(rect.bottom, containerRect.bottom) -
      Math.max(rect.top, containerRect.top);
    if (visible > bestVisible) {
      bestVisible = visible;
      bestPage = Number(page.dataset.page);
    }
  }

  return Number.isFinite(bestPage) ? bestPage : null;
}

/** 解析锚点 id，优先元素级，回退到页级 */
export function resolveScrollAnchor(
  from: HTMLElement,
  to: HTMLElement,
): { type: 'id'; id: string } | { type: 'page'; pageIdx: number } | null {
  const id = findClosestAnchorId(from);
  if (id && queryById(to, id)) {
    return { type: 'id', id };
  }

  const pageIdx = findVisiblePageIdx(from);
  if (pageIdx !== null) {
    const pageEl = to.querySelector<HTMLElement>(`[data-page="${pageIdx}"]`);
    if (pageEl) return { type: 'page', pageIdx };
  }

  return null;
}

export function scrollToAnchor(
  container: HTMLElement,
  anchor: { type: 'id'; id: string } | { type: 'page'; pageIdx: number },
  behavior: ScrollBehavior = 'auto',
) {
  if (anchor.type === 'id') {
    const el = queryById(container, anchor.id);
    if (el) scrollToElementInContainer(container, el, behavior);
    return;
  }

  const pageEl = container.querySelector<HTMLElement>(
    `[data-page="${anchor.pageIdx}"]`,
  );
  if (pageEl) scrollToElementInContainer(container, pageEl, behavior, 'start');
}
