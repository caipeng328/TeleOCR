import { pdfjs } from 'react-pdf';
import workerCode from 'pdfjs-dist/build/pdf.worker.min.mjs?raw';

let configured = false;

/** 将 worker 内联为 Blob URL，避免额外请求 pdf.worker */
export function configurePdfWorker() {
  if (configured || typeof window === 'undefined') return;
  configured = true;

  const blob = new Blob([workerCode], { type: 'text/javascript' });
  pdfjs.GlobalWorkerOptions.workerSrc = URL.createObjectURL(blob);
}
