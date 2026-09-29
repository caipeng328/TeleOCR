import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SpinnerProps {
  className?: string;
  label?: string;
}

export function Spinner({ className, label }: SpinnerProps) {
  return (
    <div className={cn('flex items-center gap-2 text-muted-foreground', className)}>
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
