import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { FileUp, ImageIcon, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SOURCE_ACCEPT } from '@/utils/sourceFile';

interface SourceDropzoneProps {
  busy?: boolean;
  busyLabel?: string;
  onFile: (file: File) => void;
  className?: string;
}

export function SourceDropzone({
  busy = false,
  busyLabel = '处理中…',
  onFile,
  className,
}: SourceDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function pick(file: File | undefined) {
    if (file && !busy) onFile(file);
  }

  function handleInputChange(e: ChangeEvent<HTMLInputElement>) {
    pick(e.target.files?.[0]);
    e.target.value = '';
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0]);
  }

  return (
    <div
      className={cn(
        'flex h-full w-full cursor-pointer flex-col items-center justify-center gap-3 bg-card px-8 text-center transition-colors',
        dragging && 'bg-primary/10',
        busy && 'cursor-wait',
        className,
      )}
      onDragOver={(e) => {
        e.preventDefault();
        if (!busy) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={busy ? undefined : handleDrop}
      onClick={() => !busy && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && !busy) {
          e.preventDefault();
          inputRef.current?.click();
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={SOURCE_ACCEPT}
        hidden
        disabled={busy}
        onChange={handleInputChange}
      />

      {/* 尺寸与右侧空态图标对齐：size-14 容器 + size-6 图标 */}
      <div
        className={cn(
          'flex size-14 items-center justify-center rounded-2xl transition-colors',
          dragging ? 'bg-primary' : 'bg-secondary',
        )}
      >
        {busy ? (
          <Loader2 className="size-6 animate-spin text-primary-ink" />
        ) : (
          <FileUp
            className={cn(
              'size-6',
              dragging ? 'text-primary-foreground' : 'text-primary-ink',
            )}
          />
        )}
      </div>

      {/* badge 绝对定位挂在文案 wrapper 下方，不占流内高度，
          左右两栏的文案才会落在同一行 */}
      <div className="relative">
        <div className="space-y-1">
          <p className="text-sm font-medium text-foreground">
            {busy ? busyLabel : '点击或拖拽文件到此处'}
          </p>
          <p className="text-xs text-muted-foreground">
            {busy
              ? '请稍候，完成后右侧将展示结果'
              : '选择后将自动开始解析 · 支持 PDF、PNG、JPG、WebP 等'}
          </p>
        </div>

        {!busy && (
          <div className="absolute inset-x-0 top-full flex items-center justify-center gap-3 pt-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-secondary-foreground">
              <FileUp className="size-3.5 text-primary-ink" />
              PDF
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-secondary-foreground">
              <ImageIcon className="size-3.5 text-primary-ink" />
              图片
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
