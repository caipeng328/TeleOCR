from tqdm import tqdm
from TeleOCR.tools.pdf_image_tools import get_page_size
from TeleOCR.src.vlm_magic_model import MagicModel
from TeleOCR.tools.cut_image import cut_image_and_table 
from TeleOCR.tools.enum_class import ContentType
from TeleOCR.tools.hash_utils import bytes_md5
from TeleOCR.version import __version__


def blocks_to_page_info(page_blocks,image_dict,page,image_writer,page_index) -> dict:
    scale = image_dict["scale"]
    page_pil_img = image_dict["img_pil"]
    page_img_md5 = bytes_md5(page_pil_img.tobytes())
    width, height = map(int, get_page_size(page))
    magic_model = MagicModel(page_blocks, width, height)
    all_spans = magic_model.get_all_spans()
    for span in all_spans:
        if span["type"] in [
            ContentType.IMAGE,
            ContentType.SEAL,
            ContentType.CHAR,
        ]:
            cut_image_and_table(span,page_pil_img,page_img_md5,page_index,image_writer,scale=scale)
    page_blocks = magic_model.get_page_blocks()
    page_info = {"para_blocks": page_blocks,"discarded_blocks": [],"page_size": [width, height],"page_idx": page_index}
    return page_info

def result_to_middle_json(model_output_blocks_list, images_list, pdf_doc, image_writer):
    middle_json = {"pdf_info": [],"_backend": "vlm","_version_name": __version__,}
    try:
        for index, page_blocks in enumerate(tqdm(model_output_blocks_list)):
            page = pdf_doc[index]
            try:
                image_dict = images_list[index]
                page_info = blocks_to_page_info(
                    page_blocks, image_dict, page, image_writer, index
                )
                middle_json['pdf_info'].append(page_info)
            finally:
                page.close()
    finally:
        pdf_doc.close()
    return middle_json
