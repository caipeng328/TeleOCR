from enum import Enum

class BlockType:
    IMAGE = 'image'
    TABLE = 'table'
    IMAGE_BODY = 'image_body'
    TABLE_BODY = 'table_body'
    IMAGE_CAPTION = 'image_caption'
    TABLE_CAPTION = 'table_caption'
    IMAGE_FOOTNOTE = 'image_footnote'
    TABLE_FOOTNOTE = 'table_footnote'
    TEXT = 'text' 
    TITLE = 'title'
    INTERLINE_EQUATION = 'interline_equation'
    LIST = 'list'
    INDEX = 'index'
    DISCARDED = 'discarded'

    CODE = "code"
    CODE_BODY = "code_body"
    CODE_CAPTION = "code_caption"
    ALGORITHM = "algorithm"
    REF_TEXT = "ref_text"
    PHONETIC = "phonetic"
    HEADER = "header"
    FOOTER = "footer"
    PAGE_NUMBER = "page_number"
    ASIDE_TEXT = "aside_text"
    PAGE_FOOTNOTE = "page_footnote"
    SEAL = 'seal'
    CHAR = 'char'

class ContentType:
    IMAGE = 'image'
    TABLE = 'table'
    TEXT = 'text'
    INTERLINE_EQUATION = 'interline_equation'
    INLINE_EQUATION = 'inline_equation'
    EQUATION = 'equation'
    CODE = 'code'
    SEAL = 'seal'
    CHAR = 'char'

class SplitFlag:
    CROSS_PAGE = 'cross_page'
    LINES_DELETED = 'lines_deleted'


class ImageType:
    PIL = 'pil_img'
    BASE64 = 'base64_img'


class NotExtractType(Enum):
    TEXT = BlockType.TEXT
    TITLE = BlockType.TITLE
    HEADER = BlockType.HEADER
    FOOTER = BlockType.FOOTER
    PAGE_NUMBER = BlockType.PAGE_NUMBER
    PAGE_FOOTNOTE = BlockType.PAGE_FOOTNOTE
    REF_TEXT = BlockType.REF_TEXT
    TABLE_CAPTION = BlockType.TABLE_CAPTION
    IMAGE_CAPTION = BlockType.IMAGE_CAPTION
    TABLE_FOOTNOTE = BlockType.TABLE_FOOTNOTE
    IMAGE_FOOTNOTE = BlockType.IMAGE_FOOTNOTE
    CODE_CAPTION = BlockType.CODE_CAPTION

