import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface IconSwapProps {
  /** a = 默认图标，b = 忙碌/loader 图标 */
  state: 'a' | 'b';
  iconA: ReactNode;
  iconB: ReactNode;
  className?: string;
}

/** Transitions.dev Icon swap：data-state 切换时带 blur/scale 过渡 */
export function IconSwap({ state, iconA, iconB, className }: IconSwapProps) {
  return (
    <span className={cn('t-icon-swap', className)} data-state={state}>
      <span className="t-icon size-3.5 [&_svg]:size-3.5" data-icon="a">
        {iconA}
      </span>
      <span className="t-icon size-3.5 [&_svg]:size-3.5" data-icon="b">
        {iconB}
      </span>
    </span>
  );
}
