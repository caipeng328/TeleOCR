import importlib

import fitz
import pytest

import TeleOCR.config as config
from TeleOCR.tools.enum_class import ImageType
from TeleOCR.tools.pdf_executor import shutdown_pdf_workers


@pytest.mark.parametrize('backend', ['pdfium', 'PyMuPDF'])
def test_real_pdf_page_order_and_pixels_match_serial_renderer(backend, monkeypatch):
    monkeypatch.setattr(config, 'PDF_TOOLS_WORKER_MAX_NUM', 2)
    monkeypatch.setattr(config, 'MAX_PIXELS', 1000000)
    module = importlib.import_module(f'TeleOCR.tools.pdf_image_tools_{backend}')
    pdf = fitz.open()
    for text in ['First page', 'Second page']:
        page = pdf.new_page(width=240, height=320)
        page.insert_text((25, 40), text)
    data = pdf.tobytes()
    pdf.close()
    expected = module.load_images_from_pdf_core(data, dpi=72, image_type=ImageType.PIL)
    try:
        for _ in range(2):
            actual, document = module.load_images_from_pdf(data, dpi=72, threads=2, timeout=20)
            try:
                assert len(actual) == 2
                for reference, image in zip(expected, actual):
                    assert image['scale'] == reference['scale']
                    assert image['img_pil'].size == reference['img_pil'].size
                    assert image['img_pil'].tobytes() == reference['img_pil'].tobytes()
            finally:
                document.close()
                for image in actual:
                    image['img_pil'].close()
    finally:
        for image in expected:
            image['img_pil'].close()
        shutdown_pdf_workers()
