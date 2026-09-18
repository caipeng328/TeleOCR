import asyncio
import os
import threading
import time

import pytest

from TeleOCR.tools.pdf_executor import run_pdf_cpu, shared_pdf_executor, shutdown_pdf_workers


def worker_pid():
    time.sleep(0.02)
    return os.getpid()


def worker_pixels():
    import TeleOCR.config as config
    return config.MAX_PIXELS


@pytest.fixture(autouse=True)
def cleanup_pool():
    shutdown_pdf_workers()
    yield
    shutdown_pdf_workers()


def test_processes_are_reused_across_documents():
    groups = []
    for _ in range(3):
        with shared_pdf_executor(2) as pool:
            groups.append({future.result(timeout=20) for future in
                           [pool.submit(worker_pid), pool.submit(worker_pid)]})
    assert 1 <= len(set.union(*groups)) <= 2
    assert groups[1] <= groups[0]
    assert groups[2] <= groups[0]


def test_config_change_requires_explicit_shutdown():
    with shared_pdf_executor(1):
        pass
    with pytest.raises(RuntimeError, match='shutdown_pdf_workers'):
        with shared_pdf_executor(2):
            pass


def test_spawn_workers_receive_runtime_overrides(monkeypatch):
    import TeleOCR.config as config
    with shared_pdf_executor(1) as pool:
        for value in (123456, 654321):
            monkeypatch.setattr(config, 'MAX_PIXELS', value)
            assert pool.submit(worker_pixels).result(timeout=20) == value


def test_request_failure_does_not_shutdown_shared_workers():
    closed = []
    with shared_pdf_executor(1) as pool:
        pid = pool.submit(worker_pid).result(timeout=20)
    with pytest.raises(TimeoutError):
        with shared_pdf_executor(1, on_error=lambda: closed.append(True)):
            raise TimeoutError('request timed out')
    with shared_pdf_executor(1) as pool:
        assert pool.submit(worker_pid).result(timeout=20) == pid
    assert closed == [True]


def test_running_jobs_keep_admission_after_cancel(monkeypatch):
    from concurrent.futures import Future
    import TeleOCR.tools.pdf_executor as module
    submitted = []
    class FakePool:
        def __init__(self, **kwargs):
            assert kwargs['mp_context'].get_start_method() == 'spawn'
        def submit(self, *args):
            future = Future()
            future.set_running_or_notify_cancel()
            submitted.append(future)
            return future
    monkeypatch.setattr(module, 'ProcessPoolExecutor', FakePool)
    pool = module._RenderExecutor(1)
    first = pool.submit(worker_pid)
    assert not first.cancel()
    started, finished = threading.Event(), threading.Event()
    def submit_second():
        started.set()
        pool.submit(worker_pid)
        finished.set()
    thread = threading.Thread(target=submit_second)
    thread.start()
    try:
        assert started.wait(1)
        assert not finished.wait(0.05)
        assert len(submitted) == 1
    finally:
        first.set_result(1)
        thread.join(timeout=2)
    assert finished.is_set()
    submitted[1].set_result(2)


def test_saturated_worker_admission_times_out_without_releasing_running_slot(monkeypatch):
    from concurrent.futures import Future
    import TeleOCR.tools.pdf_executor as module
    class FakePool:
        def __init__(self, **kwargs):
            pass
        def submit(self, *args):
            future = Future()
            future.set_running_or_notify_cancel()
            return future
    monkeypatch.setattr(module, 'ProcessPoolExecutor', FakePool)
    pool = module._RenderExecutor(1)
    first = pool.submit(worker_pid)
    with pytest.raises(TimeoutError, match='waiting for a PDF render worker'):
        pool.submit(worker_pid, admission_timeout=0.02)
    assert not first.done()
    first.set_result(1)
    second = pool.submit(worker_pid, admission_timeout=0.02)
    second.set_result(2)


@pytest.mark.asyncio
async def test_cpu_work_does_not_block_loop_and_uses_one_native_thread():
    loop_thread = threading.get_ident()
    started, release = threading.Event(), threading.Event()
    def work():
        started.set()
        assert release.wait(5)
        return threading.get_ident()
    task = asyncio.create_task(run_pdf_cpu(work))
    try:
        for _ in range(100):
            if started.is_set():
                break
            await asyncio.sleep(0.01)
        assert started.is_set()
        assert not task.done()
    finally:
        release.set()
    first_thread = await task
    assert first_thread != loop_thread
    assert await run_pdf_cpu(threading.get_ident) == first_thread


@pytest.mark.asyncio
async def test_repeated_cancellation_drains_and_closes_unclaimed_result():
    started, release = threading.Event(), threading.Event()
    closed = []
    def work():
        started.set()
        assert release.wait(5)
        return 'resource'
    task = asyncio.create_task(run_pdf_cpu(work, on_cancel=closed.append))
    try:
        while not started.is_set():
            await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0.01)
        task.cancel()
        await asyncio.sleep(0.01)
        assert not task.done()
        assert not closed
    finally:
        release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed == ['resource']


@pytest.mark.asyncio
async def test_cpu_exception_propagates_and_lane_remains_usable():
    def fail():
        raise ValueError('render failed')
    with pytest.raises(ValueError, match='render failed'):
        await run_pdf_cpu(fail)
    assert await run_pdf_cpu(lambda: 42) == 42
