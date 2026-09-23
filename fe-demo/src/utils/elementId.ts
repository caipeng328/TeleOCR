/** 生成跨页唯一的元素 ID */
export function makeElementId(
  pageIdx: number,
  blockIndex: number,
  spanIndex?: number,
): string {
  if (spanIndex !== undefined) {
    return `p${pageIdx}-${blockIndex}-span-${spanIndex}`;
  }
  return `p${pageIdx}-${blockIndex}`;
}

/** list 等容器内嵌套条目的 ID */
export function makeNestedItemId(
  pageIdx: number,
  parentIndex: number,
  itemIndex: number,
): string {
  return `p${pageIdx}-${parentIndex}-item-${itemIndex}`;
}
