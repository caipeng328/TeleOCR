
import os
from io import BytesIO

import numpy as np
import pypdfium2 as pdfium
import io
from loguru import logger
from PIL import Image, ImageOps

import TeleOCR.config as CONFIG
from TeleOCR.tools.check_sys_env import is_windows_environment
from TeleOCR.tools.os_env_config import get_load_images_timeout
from TeleOCR.tools.pdf_reader import image_to_b64str, image_to_bytes, page_to_image
from TeleOCR.tools.enum_class import ImageType
from TeleOCR.tools.hash_utils import str_sha256
from TeleOCR.tools.pdf_page_id import get_end_page_id
from concurrent.futures import ProcessPoolExecutor, TimeoutError as FuturesTimeoutError

def convert_pdf_bytes_to_bytes(pdf_bytes, valid_single_page_ids=None):
    pdf = pdfium.PdfDocument(pdf_bytes)
    output_pdf = pdfium.PdfDocument.new()

    try:
        total_pages = len(pdf)
        if not valid_single_page_ids:
            valid_single_page_ids = list(range(total_pages))

        valid_single_page_ids = [page_id for page_id in valid_single_page_ids if 0 <= page_id < total_pages]

        for page_index in valid_single_page_ids:
            try:
                output_pdf.import_pages(pdf, pages=[page_index])
            except Exception as page_error:
                logger.warning(
                    f"Failed to import page {page_index}: "
                    f"{page_error}, skipping this page."
                )

        output_buffer = io.BytesIO()
        output_pdf.save(output_buffer)
        output_bytes = output_buffer.getvalue()

    except Exception as e:
        logger.warning(
            f"Error in converting PDF bytes: {e}, "
            f"Using original PDF bytes."
        )
        output_bytes = pdf_bytes

    pdf.close()
    output_pdf.close()

    return output_bytes

def pdf_page_to_image(page: pdfium.PdfPage, dpi=200, image_type=ImageType.PIL) -> dict:
    """Convert pdfium.PdfDocument to image, Then convert the image to base64.

    Args:
        page (_type_): pdfium.PdfPage
        dpi (int, optional): reset the dpi of dpi. Defaults to 200.
        image_type (ImageType, optional): The type of image to return. Defaults to ImageType.PIL.

    Returns:
        dict:  {'img_base64': str, 'img_pil': pil_img, 'scale': float }
    """
    pil_img, scale = page_to_image(page, dpi=dpi)
    image_dict = {
        "scale": scale,
    }
    if image_type == ImageType.BASE64:
        image_dict["img_base64"] = image_to_b64str(pil_img)
    else:
        image_dict["img_pil"] = pil_img

    return image_dict


def _load_images_from_pdf_worker(
    pdf_bytes, dpi, start_page_id, end_page_id, image_type
):
    """用于进程池的包装函数"""
    return load_images_from_pdf_core(
        pdf_bytes, dpi, start_page_id, end_page_id, image_type
    )


def load_images_from_pdf(
    pdf_bytes: bytes,
    dpi=200,
    start_page_id=0,
    end_page_id=None,
    image_type=ImageType.PIL,
    timeout=None,
    threads=4,
):
    """带超时控制的 PDF 转图片函数,支持多进程加速

    Args:
        pdf_bytes (bytes): PDF 文件的 bytes
        dpi (int, optional): reset the dpi of dpi. Defaults to 200.
        start_page_id (int, optional): 起始页码. Defaults to 0.
        end_page_id (int | None, optional): 结束页码. Defaults to None.
        image_type (ImageType, optional): 图片类型. Defaults to ImageType.PIL.
        timeout (int | None, optional): 超时时间(秒)。如果为 None，则从环境变量 TeleOCR_PDF_LOAD_IMAGES_TIMEOUT 读取，若未设置则默认为 300 秒。
        threads (int): 进程数,默认 4

    Raises:
        TimeoutError: 当转换超时时抛出
    """
    pdf_doc = pdfium.PdfDocument(pdf_bytes)
    if is_windows_environment() or CONFIG.PDF_TOOLS_WORKER_MAX_NUM==0:
        # Windows 环境下不使用多进程
        return load_images_from_pdf_core(
            pdf_bytes,
            dpi,
            start_page_id,
            get_end_page_id(end_page_id, len(pdf_doc)),
            image_type,
        ), pdf_doc
    else:
        if timeout is None:
            timeout = get_load_images_timeout()
        end_page_id = get_end_page_id(end_page_id, len(pdf_doc))

        # 计算总页数
        total_pages = end_page_id - start_page_id + 1

        # 实际使用的进程数不超过总页数
        actual_threads = min(max(1, int(os.cpu_count() * CONFIG.PDF_TOOLS_WORKER_RATIO)), threads, total_pages)

        # 根据实际进程数分组页面范围
        pages_per_thread = max(1, total_pages // actual_threads)
        page_ranges = []

        for i in range(actual_threads):
            range_start = start_page_id + i * pages_per_thread
            if i == actual_threads - 1:
                # 最后一个进程处理剩余所有页面
                range_end = end_page_id
            else:
                range_end = start_page_id + (i + 1) * pages_per_thread - 1

            page_ranges.append((range_start, range_end))


        with ProcessPoolExecutor(max_workers=actual_threads) as executor:
            # 提交所有任务
            futures = []
            for range_start, range_end in page_ranges:
                future = executor.submit(
                    _load_images_from_pdf_worker,
                    pdf_bytes,
                    dpi,
                    range_start,
                    range_end,
                    image_type,
                )
                futures.append((range_start, future))

            try:
                # 收集结果并按页码排序
                all_results = []
                for range_start, future in futures:
                    images_list = future.result(timeout=timeout)
                    all_results.append((range_start, images_list))

                # 按起始页码排序并合并结果
                all_results.sort(key=lambda x: x[0])
                images_list = []
                for _, imgs in all_results:
                    images_list.extend(imgs)

                return images_list, pdf_doc
            except FuturesTimeoutError:
                pdf_doc.close()
                executor.shutdown(wait=False, cancel_futures=True)
                raise TimeoutError(f"PDF to images conversion timeout after {timeout}s")


def load_images_from_pdf_core(
    pdf_bytes: bytes,
    dpi=200,
    start_page_id=0,
    end_page_id=None,
    image_type=ImageType.PIL,  # PIL or BASE64
):
    images_list = []
    pdf_doc = pdfium.PdfDocument(pdf_bytes)
    pdf_page_num = len(pdf_doc)
    end_page_id = get_end_page_id(end_page_id, pdf_page_num)

    for index in range(start_page_id, end_page_id + 1):
        # logger.debug(f"Converting page {index}/{pdf_page_num} to image")
        page = pdf_doc[index]
        image_dict = pdf_page_to_image(page, dpi=dpi, image_type=image_type)
        images_list.append(image_dict)

    pdf_doc.close()

    return images_list


def cut_image(
    bbox: tuple,
    page_num: int,
    page_pil_img,
    return_path,
    image_writer,
    scale=2,
):
    filename = f"{page_num}_{int(bbox[0])}_{int(bbox[1])}_{int(bbox[2])}_{int(bbox[3])}"
    rel_img_path = f"{return_path}_{filename}.jpeg" if return_path is not None else None
    crop_img = get_crop_img(bbox, page_pil_img, scale=scale)
    img_bytes = image_to_bytes(crop_img, image_format="JPEG")
    image_writer.add_image(img_bytes, rel_img_path) 
    return rel_img_path


def get_crop_img(bbox: tuple, pil_img, scale=2):
    scale_bbox = (
        int(bbox[0] * scale),
        int(bbox[1] * scale),
        int(bbox[2] * scale),
        int(bbox[3] * scale),
    )
    return pil_img.crop(scale_bbox)


# def get_crop_np_img(bbox: tuple, input_img, scale=2):
#     if isinstance(input_img, Image.Image):
#         np_img = np.asarray(input_img)
#     elif isinstance(input_img, np.ndarray):
#         np_img = input_img
#     else:
#         raise ValueError("Input must be a pillow object or a numpy array.")

#     scale_bbox = (
#         int(bbox[0] * scale),
#         int(bbox[1] * scale),
#         int(bbox[2] * scale),
#         int(bbox[3] * scale),
#     )

#     return np_img[scale_bbox[1] : scale_bbox[3], scale_bbox[0] : scale_bbox[2]]


def images_bytes_to_pdf_bytes(image_bytes):
    pdf_buffer = BytesIO()
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image) or image
    if image.mode != "RGB":
        image = image.convert("RGB")
    # 第一张图保存为 PDF，其余追加
    image.save(
        pdf_buffer,
        format="PDF",
        # save_all=True
    )
    # 获取 PDF bytes 并重置指针（可选）
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()
    return pdf_bytes

def get_page_size(page):
    w, h = page.get_size()
    return (w, h)
    