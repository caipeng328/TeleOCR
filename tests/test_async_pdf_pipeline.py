"""Exercise async orchestration without importing a GPU model dependency."""
import ast
import asyncio
from pathlib import Path
import threading
import time
from types import SimpleNamespace

import pytest

from TeleOCR.tools.pdf_executor import run_pdf_cpu


def load_functions(relative, namespace):
    tree = ast.parse((Path(__file__).parents[1] / relative).read_text())
    definitions = [node for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    exec(compile(ast.Module(body=definitions, type_ignores=[]), relative, 'exec'), namespace)
    return namespace


@pytest.mark.asyncio
@pytest.mark.parametrize('inference_fails', [False, True])
async def test_render_and_projection_off_loop_inference_on_loop_and_resources_closed(inference_fails):
    loop_thread = threading.get_ident()
    cpu_threads = []
    closed = []
    class PDF:
        is_closed = False
        def close(self):
            assert threading.get_ident() != loop_thread
            self.is_closed = True
            closed.append('pdf')
    class Image:
        def close(self):
            closed.append('image')
    pdf, image = PDF(), Image()
    def render(*args, **kwargs):
        cpu_threads.append(threading.get_ident())
        return [{'img_pil': image}], pdf
    def project(results, images, document, writer):
        cpu_threads.append(threading.get_ident())
        assert results == ['recognized']
        return {'pdf_info': ['preserved']}
    class Predictor:
        async def aio_batch_two_step_extract(self, images):
            assert threading.get_ident() == loop_thread
            assert images == [image]
            await asyncio.sleep(0)
            if inference_fails:
                raise ValueError('inference failed')
            return ['recognized']
    namespace = load_functions('TeleOCR/src/vlm_analyze.py', {
        'time': time, 'run_pdf_cpu': run_pdf_cpu,
        'ImageType': SimpleNamespace(PIL='pil'), 'DataWriter': object,
        'CONFIG': SimpleNamespace(PDF_TOOLS_WORKER_MAX_NUM=2),
        'logger': SimpleNamespace(debug=lambda *_: None),
        'load_images_from_pdf': render, 'result_to_middle_json': project,
    })
    if inference_fails:
        with pytest.raises(ValueError, match='inference failed'):
            await namespace['aio_doc_analyze'](b'pdf', predictor=Predictor())
    else:
        assert await namespace['aio_doc_analyze'](b'pdf', predictor=Predictor()) == {'pdf_info': ['preserved']}
    assert closed == ['pdf', 'image']
    assert len(set(cpu_threads)) == 1
    assert cpu_threads[0] != loop_thread


@pytest.mark.asyncio
async def test_engine_preparation_is_offloaded_before_async_inference():
    loop_thread = threading.get_ident()
    def prepare(data, page_ids):
        assert threading.get_ident() != loop_thread
        return [b'normalized']
    async def process(directory, names, data, **kwargs):
        assert threading.get_ident() == loop_thread
        assert data == [b'normalized']
        return ['result']
    namespace = load_functions('TeleOCR/engine.py', {'run_pdf_cpu': run_pdf_cpu})
    namespace['_prepare_pdf_bytes'] = prepare
    namespace['_async_process_vlm'] = process
    assert await namespace['aio_do_parse']('out', ['doc'], [b'input'], [None]) == ['result']
