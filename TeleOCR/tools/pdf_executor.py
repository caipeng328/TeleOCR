"""Reusable CPU workers for PDF processing (never run CUDA in these workers)."""
import asyncio
import atexit
import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import contextmanager
from functools import partial

_native = ThreadPoolExecutor(max_workers=1, thread_name_prefix="teleocr-pdf")
_lock = threading.Lock()
_render = None


async def run_pdf_cpu(function, *args, on_cancel=None, **kwargs):
    """Serialize native PDF calls off-loop; cancellation drains native work.

    PDFium/PyMuPDF objects stay on one thread. Draining prevents a caller's
    finally block from deleting files still used by a native operation.
    """
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(_native, partial(function, *args, **kwargs))
    cancelled = False
    while not future.done():
        try:
            await asyncio.shield(future)
        except asyncio.CancelledError:
            cancelled = True
        except Exception:
            break
    if cancelled:
        if future.exception() is None and on_cancel is not None:
            cleanup = loop.run_in_executor(_native, on_cancel, future.result())
            while not cleanup.done():
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    pass
            cleanup.result()
        raise asyncio.CancelledError
    return future.result()


def _call_render(function, args, config_values):
    # spawn does not inherit runtime overrides from the parent process.
    import TeleOCR.config as config
    for name, value in config_values.items():
        setattr(config, name, value)
    return function(*args)


class _RenderExecutor:
    def __init__(self, workers):
        self.workers = workers
        self.slots = threading.BoundedSemaphore(workers)
        self.pool = ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn"))

    def submit(self, function, *args):
        import TeleOCR.config as config
        values = {k: v for k, v in vars(config).items()
                  if k.isupper() and isinstance(v, (str, int, float, bool, type(None)))}
        self.slots.acquire()
        try:
            future = self.pool.submit(_call_render, function, args, values)
        except BaseException:
            self.slots.release()
            raise
        future.add_done_callback(lambda _: self.slots.release())
        return future


@contextmanager
def shared_pdf_executor(workers, on_error=None):
    global _render
    workers = max(1, workers)
    try:
        with _lock:
            if _render is None:
                _render = _RenderExecutor(workers)
            elif _render.workers != workers:
                raise RuntimeError("Call shutdown_pdf_workers before changing the PDF worker count")
            executor = _render
        yield executor  # A document must not shut down other documents' workers.
    except BaseException:
        if on_error is not None:
            on_error()
        raise


def shutdown_pdf_workers():
    """Call after outstanding PDF work completes, before reconfiguring workers."""
    global _render
    with _lock:
        if _render is not None:
            _render.pool.shutdown(wait=True, cancel_futures=True)
            _render = None


atexit.register(shutdown_pdf_workers)
