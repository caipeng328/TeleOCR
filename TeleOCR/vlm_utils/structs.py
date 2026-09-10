from typing import Literal


class BlockType:
    TEXT = "text"  # 文本
    TITLE = "title"  # 段落标题
    TABLE = "table"  # 表格
    IMAGE = "image"  # 图像
    CODE = "code"  # 代码
    ALGORITHM = "algorithm"  # 算法/伪代码
    HEADER = "header"  # 页眉
    FOOTER = "footer"  # 页脚
    PAGE_NUMBER = "page_number"  # 页码
    PAGE_FOOTNOTE = "page_footnote"  # 脚注
    ASIDE_TEXT = "aside_text"  # 侧栏文本(装订线等)
    EQUATION = "equation"  # 公式(独立公式)
    EQUATION_BLOCK = "equation_block"  # 公式块(多行公式)
    REF_TEXT = "ref_text"  # 参考文献(一条)
    LIST = "list"  # 列表块(无序/有序列表)
    PHONETIC = "phonetic"  # 注音符号
    # captions
    TABLE_CAPTION = "table_caption"  # 表格标题
    IMAGE_CAPTION = "image_caption"  # 图像标题
    CODE_CAPTION = "code_caption"    # 代码标题
    TABLE_FOOTNOTE = "table_footnote"  # 表格脚注
    IMAGE_FOOTNOTE = "image_footnote"  # 图像脚注
    UNKNOWN = "unknown"  # 未知块
    SEAL = "seal" # 章
    CHAR = "char" # 科学图


BLOCK_TYPES = set(
    [
        BlockType.TEXT,
        BlockType.TITLE,
        BlockType.TABLE,
        BlockType.IMAGE,
        BlockType.CODE,
        BlockType.HEADER,
        BlockType.FOOTER,
        BlockType.PAGE_NUMBER,
        BlockType.PAGE_FOOTNOTE,
        BlockType.ASIDE_TEXT,
        BlockType.EQUATION,
        BlockType.EQUATION_BLOCK,
        BlockType.REF_TEXT,
        BlockType.TABLE_CAPTION,
        BlockType.IMAGE_CAPTION,
        BlockType.TABLE_FOOTNOTE,
        BlockType.IMAGE_FOOTNOTE,
        BlockType.ALGORITHM,
        BlockType.CODE_CAPTION,
        BlockType.LIST,
        BlockType.PHONETIC,
        BlockType.UNKNOWN,
        BlockType.SEAL,
        BlockType.CHAR,
    ]
)

ANGLE_OPTIONS = set([None, 0, 90, 180, 270])


class ContentBlock(dict):
    def __init__(
        self,
        type: str,
        bbox: list[list],
        angle: Literal[None, 0, 90, 180, 270] = None,
        content: str | None = None,
    ):
        """
        Initialize a layout block.
        Args:
            type (str): Type of the block (e.g., 'text', 'image', 'table').
            bbox (list[float]): Bounding box coordinates [xmin, ymin, xmax, ymax].
            angle (int or None): Rotation angle of the block. Must be one of {None, 0, 90, 180, 270}.
            content (str or None): The content of the block (if exists).
        """
        super().__init__()

        assert type in BLOCK_TYPES, f"Unknown type: {type}"
        assert angle in ANGLE_OPTIONS, f"Invalid angle: {angle}. Must be one of {ANGLE_OPTIONS}"
        assert content is None or isinstance(content, str), "Content must be a string or None"

        self["type"] = type
        self["bbox"] = bbox
        self["angle"] = angle
        self["content"] = content

    @property
    def type(self) -> str:
        return self["type"]

    @type.setter
    def type(self, value: str):
        assert value in BLOCK_TYPES, f"Unknown type: {value}"
        self["type"] = value

    @property
    def bbox(self) -> list[float]:
        return self["bbox"]

    @bbox.setter
    def bbox(self, value: list[float]):
        self["bbox"] = value

    @property
    def angle(self) -> Literal[None, 0, 90, 180, 270]:
        return self["angle"]

    @angle.setter
    def angle(self, value: Literal[None, 0, 90, 180, 270]):
        assert value in ANGLE_OPTIONS, f"Invalid angle: {value}. Must be one of {ANGLE_OPTIONS}"
        self["angle"] = value

    @property
    def content(self) -> str | None:
        return self["content"]

    @content.setter
    def content(self, value: str | None):
        assert value is None or isinstance(value, str), "Content must be a string or None"
        self["content"] = value
