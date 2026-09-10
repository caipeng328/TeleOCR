import json
import os
import time
from loguru import logger

from TeleOCR.tools.pdf_image_tools import convert_pdf_bytes_to_bytes
from TeleOCR.data_reader_writer import FileBasedDataWriter, ImageDataWriter
from TeleOCR.tools.draw_bbox import draw_layout_bbox
from TeleOCR.src.vlm_middle_json_mkcontent import union_make
from TeleOCR.src.vlm_analyze import doc_analyze
from TeleOCR.src.vlm_analyze import aio_doc_analyze 

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def prepare_env(output_dir, pdf_file_name):
    local_md_dir = str(os.path.join(output_dir, pdf_file_name))
    local_image_dir = os.path.join(str(local_md_dir), "images")
    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(local_md_dir, exist_ok=True)
    return local_image_dir, local_md_dir


def _prepare_pdf_bytes(pdf_bytes_list, valid_page_ids):
    result = []
    for idx, pdf_bytes in enumerate(pdf_bytes_list):
        valid_single_page_ids = (
            valid_page_ids[idx]
            if valid_page_ids and idx < len(valid_page_ids)
            else None
        )
        new_pdf_bytes = convert_pdf_bytes_to_bytes(pdf_bytes, valid_single_page_ids)
        result.append(new_pdf_bytes)
    return result


def _process_output(
        pdf_info,
        pdf_bytes,
        pdf_file_name,
        local_md_dir,
        local_image_dir,
        md_writer,
        middle_json,
        f_draw_layout_bbox=True,
        f_dump_md=True,
        f_dump_middle_json=True,
):
    if f_draw_layout_bbox:
        draw_layout_bbox(pdf_info, pdf_bytes, local_md_dir, f"{pdf_file_name}_layout.pdf")
    image_dir = str(os.path.basename(local_image_dir))
    if f_dump_md:
        md_content_str = union_make(pdf_info, image_dir) 
        md_writer.write_string(
            f"{pdf_file_name}.md",
            md_content_str,
        )
    if f_dump_middle_json:
        md_writer.write_string(
            f"{pdf_file_name}_middle.json",
            json.dumps(middle_json, ensure_ascii=False, indent=4),
        )
    logger.info(f"local output dir is {local_md_dir}")

async def _async_process_vlm(output_dir, pdf_file_names, pdf_bytes_list, **kwargs,):
    results = []
    for idx, pdf_bytes in enumerate(pdf_bytes_list):
        pdf_file_name = pdf_file_names[idx]
        local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name)
        image_writer = ImageDataWriter(local_image_dir)
        vlm_doc_analyze_time = time.time()
        middle_json = await aio_doc_analyze(
            pdf_bytes, image_writer=image_writer, **kwargs,
        )
        vlm_doc_analyze_time = round(time.time() - vlm_doc_analyze_time, 2)
        logger.debug(f"doc_analyze cost: {vlm_doc_analyze_time}")
        
        pdf_info = middle_json["pdf_info"]
        md_writer = FileBasedDataWriter(local_md_dir)
        
        process_output_time = time.time()
        _process_output(
            pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
            md_writer, middle_json
        )
        image_writer.save_all_images()
        process_output_time = round(time.time() - process_output_time, 2)
        logger.debug(f"process_output_time cost: {process_output_time}")
        results.append(middle_json)
    return results


def _process_vlm(output_dir, pdf_file_names, pdf_bytes_list, **kwargs,):
    results = []
    for idx, pdf_bytes in enumerate(pdf_bytes_list):
        pdf_file_name = pdf_file_names[idx]
        local_image_dir, local_md_dir = prepare_env(output_dir, pdf_file_name)
        image_writer = ImageDataWriter(local_image_dir)
        
        vlm_doc_analyze_time = time.time()
        middle_json = doc_analyze(
            pdf_bytes, image_writer=image_writer, **kwargs,
        )
        vlm_doc_analyze_time = round(time.time() - vlm_doc_analyze_time, 2)
        logger.debug(f"doc_analyze cost: {vlm_doc_analyze_time}")
        
        pdf_info = middle_json["pdf_info"]
        md_writer = FileBasedDataWriter(local_md_dir)
        
        process_output_time =  time.time()
        _process_output(
            pdf_info, pdf_bytes, pdf_file_name, local_md_dir, local_image_dir,
            md_writer, middle_json
        )
        image_writer.save_all_images()
        process_output_time = round(time.time() - process_output_time, 2)
        logger.debug(f"process_output_time cost: {process_output_time}")
        
        results.append(middle_json)
    return results


def inplace_change_page_ids(results, valid_page_ids):
    for result, valid_page_id in zip(results, valid_page_ids):
        if valid_page_id is None:
            continue
        for page in result.get("pages", []):
            page_id = page.get("page_id")
            if (
                isinstance(page_id, int)
                and 0 <= page_id < len(valid_page_id)
            ):
                page["page_id"] = valid_page_id[page_id]
    return results


async def aio_do_parse( 
        output_dir,
        pdf_file_names: list[str],
        pdf_bytes_list: list[bytes],
        valid_page_ids: list[list[int] | None],
        **kwargs,
):
    pdf_bytes_list = _prepare_pdf_bytes(pdf_bytes_list, valid_page_ids)
    Results = await _async_process_vlm(
        output_dir, pdf_file_names, pdf_bytes_list, **kwargs,
    )
    return Results


def do_parse(
        output_dir,
        pdf_file_names: list[str],
        pdf_bytes_list: list[bytes],
        valid_page_ids: list[list[int] | None],
        **kwargs,
):
    pdf_bytes_list = _prepare_pdf_bytes(pdf_bytes_list, valid_page_ids)
    Results = _process_vlm(
        output_dir, pdf_file_names, pdf_bytes_list, **kwargs,
    )
    return Results
