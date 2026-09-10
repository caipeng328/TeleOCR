from .guess_suffix_or_lang import guess_suffix_by_bytes
from .pdf_image_tools import images_bytes_to_pdf_bytes
from pathlib import Path

pdf_suffixes = ["pdf"]
image_suffixes = ["png", "jpeg", "jp2", "webp", "gif", "bmp", "jpg", "tiff"]



def read_fn(path):
    if not isinstance(path, Path):
        path = Path(path)
    with open(str(path), "rb") as input_file:
        file_bytes = input_file.read()
        file_suffix = guess_suffix_by_bytes(file_bytes, path)
        if file_suffix in image_suffixes:
            return images_bytes_to_pdf_bytes(file_bytes)
        elif file_suffix in pdf_suffixes:
            return file_bytes
        else:
            raise Exception(f"Unknown file suffix: {file_suffix}")