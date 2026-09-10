import importlib

import TeleOCR.config as CONFIG

PDF_MODULES = {
    "PyMuPDF": ".pdf_image_tools_PyMuPDF",
    "pypdfium2": ".pdf_image_tools_pdfium",
}

module = importlib.import_module(
    PDF_MODULES[CONFIG.PDF_TOOLS],
    package=__package__,
)

for name in (
    "pdf_page_to_image",
    "_load_images_from_pdf_worker",
    "load_images_from_pdf",
    "load_images_from_pdf_core",
    "cut_image",
    "get_crop_img",
    "images_bytes_to_pdf_bytes",
    "get_page_size",
    "convert_pdf_bytes_to_bytes"
):
    globals()[name] = getattr(module, name)