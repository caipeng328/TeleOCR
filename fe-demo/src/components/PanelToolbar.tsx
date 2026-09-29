import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PanelToolbarProps {
  title?: string;
  children?: ReactNode;
  className?: string;
}

/** 对比面板顶部功能栏，预留给操作按钮 */
export function PanelToolbar({ title, children, className }: PanelToolbarProps) {
  return (
    <div
      className={cn(
        'flex h-11 shrink-0 items-center gap-2 border-b border-toolbar-border bg-toolbar px-3 text-toolbar-foreground',
        className,
      )}
    >
      {title ? (
        <span className="mr-1 truncate text-xs font-semibold uppercase tracking-wider text-primary">
          {title}
        </span>
      ) : null}
      <div
        className={cn(
          'flex min-w-0 flex-1 items-center gap-2',
          title ? 'justify-end' : 'justify-start',
        )}
      >
        {children}
      </div>
    </div>
  );
}
