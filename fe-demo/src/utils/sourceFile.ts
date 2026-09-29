export type SourceKind = 'pdf' | 'image';

/** 文件选择框与拖拽共用的 accept 列表 */
export const SOURCE_ACCEPT =
  'application/pdf,.pdf,image/png,image/jpeg,image/jpg,image/webp,image/gif,image/bmp,.png,.jpg,.jpeg,.webp,.gif,.bmp';

function isPdfFile(file: File): boolean {
  return file.type === 'application/pdf' || /\.pdf$/i.test(file.name);
}

function isImageFile(file: File): boolean {
  return (
    file.type.startsWith('image/') ||
    /\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name)
  );
}

/** 识别来源文件类型，不支持的格式返回 null */
export function resolveSourceKind(file: File): SourceKind | null {
  if (isPdfFile(file)) return 'pdf';
  if (isImageFile(file)) return 'image';
  return null;
}

/** 去掉扩展名，用作文档标题 */
export function stripExtension(name: string): string {
  return name.replace(/\.[^.]+$/, '');
}
