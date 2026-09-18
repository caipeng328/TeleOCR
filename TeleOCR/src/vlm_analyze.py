import time
from loguru import logger
from ..data_reader_writer import DataWriter
from ..tools.enum_class import ImageType
from .model_output_to_middle_json import result_to_middle_json
from TeleOCR.vlm_utils.TeleOCR_model import TeleOCRMODEL_SERVICE
from TeleOCR.tools.pdf_image_tools import load_images_from_pdf
import TeleOCR.config as CONFIG
from TeleOCR.tools.pdf_executor import run_pdf_cpu


def _close_pdf(pdf):
    if not getattr(pdf, "is_closed", False):
        pdf.close()


def _close_loaded(loaded):
    images, pdf = loaded
    _close_pdf(pdf)
    for image in images:
        image["img_pil"].close()

def _init_model():
    backend=CONFIG.BACKEND
    model_path = CONFIG.model_path
    predictor = TeleOCRMODEL_SERVICE.get_model(backend, model_path, None)
    return predictor

async def aio_doc_analyze(
    pdf_bytes, 
    predictor = None,
    image_writer = None,
):  
    if predictor is None:
        predictor = _init_model()
    load_images_start = time.time()
    images_list, pdf_doc = await run_pdf_cpu(
        load_images_from_pdf, pdf_bytes, image_type=ImageType.PIL,
        threads=CONFIG.PDF_TOOLS_WORKER_MAX_NUM, on_cancel=_close_loaded)
    images_pil_list = [image_dict["img_pil"] for image_dict in images_list]
    load_images_time = round(time.time() - load_images_start, 2)
    logger.debug(f"load images cost: {load_images_time}, speed: {round(load_images_time/len(images_pil_list), 3)} images/s")
    infer_start = time.time()
    try:
        results = await predictor.aio_batch_two_step_extract(images=images_pil_list)
        infer_time = round(time.time() - infer_start, 2)
        logger.debug(f"infer finished, cost: {infer_time}, speed: {round(infer_time / len(results), 3)} page/s")
        output_start = time.time()
        middle_json = await run_pdf_cpu(
            result_to_middle_json, results, images_list, pdf_doc, image_writer)
        output_time = round(time.time() - output_start, 2)
        logger.debug(f"output json finished, cost: {output_time}, speed: {round(output_time / len(results), 3)} page/s")
        return middle_json
    finally:
        await run_pdf_cpu(_close_loaded, (images_list, pdf_doc))


def doc_analyze(
    pdf_bytes,
    image_writer: DataWriter | None,
    predictor = None,
):
    if predictor is None:
        predictor = _init_model()
    
    load_images_start = time.time()
    images_list, pdf_doc = load_images_from_pdf(pdf_bytes, image_type=ImageType.PIL, threads=CONFIG.PDF_TOOLS_WORKER_MAX_NUM)
    images_pil_list = [image_dict["img_pil"] for image_dict in images_list]
    load_images_time = round(time.time() - load_images_start, 2)
    logger.debug(f"load images cost: {load_images_time}, speed: {round(load_images_time/len(images_pil_list), 3)} images/s")

    infer_start = time.time()
    results = predictor.batch_two_step_extract(images=images_pil_list)
    infer_time = round(time.time() - infer_start, 2)
    logger.debug(f"infer finished, cost: {infer_time}, speed: {round(len(results)/infer_time, 3)} page/s")

    output_start = time.time() 
    middle_json = result_to_middle_json(results, images_list, pdf_doc, image_writer) 
    output_time = round(time.time() - output_start, 2)
    logger.debug(f"output json finished, cost: {output_time}, speed: {round(output_time / len(results), 3)} page/s")
    return middle_json
