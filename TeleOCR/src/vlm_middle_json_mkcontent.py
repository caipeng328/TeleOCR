import os

from loguru import logger

from TeleOCR.tools.char_utils import full_to_half_exclude_marks, is_hyphen_at_line_end
from TeleOCR.tools.config_reader import get_latex_delimiter_config
from TeleOCR.tools.enum_class import BlockType, ContentType
from TeleOCR.tools.language import detect_lang


def merge_para_with_text(para_block):
    block_text = ''
    for line in para_block['lines']:
        for span in line['spans']:
            if span['type'] in [ContentType.TEXT]:
                try:
                    span['content'] = full_to_half_exclude_marks(span['content'])
                except:
                    continue
                block_text += span['content']
    block_lang = detect_lang(block_text)

    para_text = ''
    for i, line in enumerate(para_block['lines']):
        for j, span in enumerate(line['spans']):
            span_type = span['type']
            content = ''
            if span_type == ContentType.TEXT:
                content = span['content']
            elif span_type == ContentType.INLINE_EQUATION:
                content = span['content']
            elif span_type == ContentType.INTERLINE_EQUATION:
                content = span['content']
            try:
                content = content.strip()
            except:
                continue
            if content:
                if span_type == ContentType.INTERLINE_EQUATION:
                    para_text += content
                    continue
                cjk_langs = {'zh', 'ja', 'ko'}
                is_last_span = j == len(line['spans']) - 1

                if block_lang in cjk_langs:  
                    if is_last_span and span_type != ContentType.INLINE_EQUATION:
                        para_text += content
                    else:
                        para_text += f'{content} '
                else:
                    if span_type in [ContentType.TEXT, ContentType.INLINE_EQUATION]:
                        if (
                                is_last_span
                                and span_type == ContentType.TEXT
                                and is_hyphen_at_line_end(content)
                        ):
                            if (
                                    i+1 < len(para_block['lines'])
                                    and para_block['lines'][i + 1].get('spans')
                                    and para_block['lines'][i + 1]['spans'][0].get('type') == ContentType.TEXT
                                    and para_block['lines'][i + 1]['spans'][0].get('content', '')
                                    and para_block['lines'][i + 1]['spans'][0]['content'][0].islower()
                            ):
                                para_text += content[:-1]
                            else:
                                para_text += content
                        else:
                            para_text += f'{content} '
    return para_text


def mk_blocks_to_markdown(para_blocks, img_buket_path=''):
    page_markdown = []
    for para_block in para_blocks:
        para_text = ''
        para_type = para_block['type']
        if para_type in [BlockType.TEXT, BlockType.INTERLINE_EQUATION, BlockType.PHONETIC, BlockType.REF_TEXT, BlockType.FOOTER, BlockType.HEADER]:
            para_text = merge_para_with_text(para_block)
        elif para_type == BlockType.LIST:
            for block in para_block['blocks']:
                item_text = merge_para_with_text(block)
                para_text += f"{item_text}  \n"
        elif para_type == BlockType.TITLE:
            title_level = get_title_level(para_block)
            para_text = f'{"#" * title_level} {merge_para_with_text(para_block)}'
        elif para_type == BlockType.IMAGE:
            has_image_footnote = any(block['type'] == BlockType.IMAGE_FOOTNOTE for block in para_block['blocks'])
            if has_image_footnote:
                for block in para_block['blocks']:  # 1st.拼image_caption
                    if block['type'] == BlockType.IMAGE_CAPTION:
                        para_text += merge_para_with_text(block) + '  \n'
                for block in para_block['blocks']:  # 2nd.拼image_body
                    if block['type'] == BlockType.IMAGE_BODY:
                        for line in block['lines']:
                            for span in line['spans']:
                                if span['type'] == ContentType.IMAGE:
                                    if span.get('image_path', ''):
                                        para_text += f"![]({img_buket_path}/{span['image_path']})"
                for block in para_block['blocks']:  # 3rd.拼image_footnote
                    if block['type'] == BlockType.IMAGE_FOOTNOTE:
                        para_text += '  \n' + merge_para_with_text(block)
            else:
                for block in para_block['blocks']: 
                    if block['type'] == BlockType.IMAGE_BODY:
                        for line in block['lines']:
                            for span in line['spans']:
                                if span['type'] == ContentType.IMAGE:
                                    if span.get('image_path', ''):
                                        para_text += f"![]({img_buket_path}/{span['image_path']})"
                for block in para_block['blocks']:
                    if block['type'] == BlockType.IMAGE_CAPTION:
                        para_text += '  \n' + merge_para_with_text(block)
        elif para_type == BlockType.TABLE:
            for block in para_block['blocks']:
                if block['type'] == BlockType.TABLE_CAPTION:
                    para_text += merge_para_with_text(block) + '  \n'
            for block in para_block['blocks']:
                if block['type'] == BlockType.TABLE_BODY:
                    for line in block['lines']:
                        for span in line['spans']:
                            if span['type'] == ContentType.TABLE:
                                if span.get('html', ''):
                                    para_text += f"\n{span['html']}\n"
                                elif span.get('image_path', ''):
                                    para_text += f"![]({img_buket_path}/{span['image_path']})"
            for block in para_block['blocks']:
                if block['type'] == BlockType.TABLE_FOOTNOTE:
                    para_text += '\n' + merge_para_with_text(block) + '  '
        elif para_type == BlockType.CODE:
            sub_type = para_block["sub_type"]
            for block in para_block['blocks']: 
                if block['type'] == BlockType.CODE_CAPTION:
                    para_text += merge_para_with_text(block) + '  \n'
            for block in para_block['blocks']: 
                if block['type'] == BlockType.CODE_BODY:
                    if sub_type == BlockType.CODE:
                        guess_lang = para_block["guess_lang"]
                        para_text += f"```{guess_lang}\n{merge_para_with_text(block)}\n```"
                    elif sub_type == BlockType.ALGORITHM:
                        para_text += merge_para_with_text(block)
        elif para_type == BlockType.CHAR: 
            for line in para_block['lines']:
                spans = line['spans']
                for span in spans:
                    content = span['content']
                    if len(content) <= 5:
                        continue
                    else:
                        para_text += f"\n{content}\n"
        if para_text.strip() == '':
            continue
        else:
            page_markdown.append(para_text.strip())

    return page_markdown


def union_make(pdf_info_dict: list,img_buket_path: str = '', ): 
    output_content = []
    for page_info in pdf_info_dict:
        paras_of_layout = page_info.get('para_blocks')

        if not paras_of_layout:
            continue
        page_markdown = mk_blocks_to_markdown(paras_of_layout, img_buket_path)
        output_content.extend(page_markdown)

    return '\n\n'.join(output_content)

def get_title_level(block):
    title_level = block.get('level', 1)
    if title_level > 4:
        title_level = 4
    elif title_level < 1:
        title_level = 0
    return title_level
