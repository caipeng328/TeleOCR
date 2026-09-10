import os
from io import BytesIO
from PIL import Image
from typing import Any, Dict, List

class ImageDataWriter:
    def __init__(self, parent_dir: str = "", format = "JPEG") -> None:

        self._parent_dir = parent_dir
        self.images = {} 
        self.format = format

    def add_image(self, img_bytes, image_name: str) -> None:
        self.images[image_name] = img_bytes

    def save_image(self, image_name: str) -> None:
        if image_name not in self.images:
            raise ValueError(f"Image {image_name} not found in memory.")

        img_bytes = self.images[image_name]
        file_path = os.path.join(self._parent_dir, image_name)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(img_bytes)

    def save_all_images(self):
        os.makedirs(self._parent_dir, exist_ok=True)
        for image_name in self.images:
            self.save_image(image_name)
        self.clear_buffer()
    
    def clear_buffer(self):
        self.images.clear()



def replace_image_path_in_json(
    contents: Any,
    mapping: Dict[str, str],
    sub_type: List[str],
    key_name: str = "image_path",
) -> Any:
    def _replace_value(filename: str) -> str:
        if filename in mapping:
            return mapping[filename]
        raise KeyError(f"Missing mapping for {filename}")

    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {
                k: _replace_value(v) if k == key_name and isinstance(v, str) else _walk(v)
                for k, v in obj.items()
            }

        if isinstance(obj, list):
            return [_walk(i) for i in obj]

        return obj

    for i, content in enumerate(contents):
        if isinstance(content, dict) and content.get("type") in sub_type:
            contents[i] = _walk(content)

    return contents