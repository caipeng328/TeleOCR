from ..structs import ContentBlock
from .equation_left_right import try_match_equation_left_right
from .equation_unbalanced_braces import try_fix_unbalanced_braces
from .otsl2html import convert_otsl_to_html
from .equation_double_dollar import wrap_with_double_dollar
from .equation_unicode_latex import unicode_to_latex
from .equation_escape_latex_special_chars import escape_latex_special_chars
from .text_fix_dollar import normalize_inline_math
from .equation_fix_begin_end import try_fix_begin_end
from .equation_remove_display_math_brackets import remove_math_brackets

PARATEXT_TYPES = {
    "header",
    "footer",
    "page_number",
    "aside_text", 
    "page_footnote",
    "unknown",
}


def _process_equation(content: str, debug: bool) -> str:
    content = remove_math_brackets(content)
    content = wrap_with_double_dollar(content)
    content = try_fix_begin_end(content)
    content = unicode_to_latex(content)
    content = try_match_equation_left_right(content, debug=debug)
    content = try_fix_unbalanced_braces(content, debug=debug)
    content = escape_latex_special_chars(content)
    return content

def remove_useless_label(html):
    html = html.replace("<html>", "").replace("</html>", "")
    html = html.replace("<body>", "").replace("</body>", "")
    html = html.replace("<thead>", "").replace("</thead>", "")
    html = html.replace("<table>", '<table border="1">')
    return html

def post_process(
    blocks: list[ContentBlock],
    simple_post_process: bool,
    handle_equation_block: bool,
    abandon_list: bool,
    abandon_paratext: bool,
    debug: bool = False,
) -> list[ContentBlock]:

    for block in blocks:
        if block.type == "equation" and block.content:
            try:
                block.content = _process_equation(block.content, debug=debug)
            except Exception as e:
                print("Warning: Failed to process equation: ", e)
                print("Content: ", block.content)
        
        if block.type == "text" and block.content:
            try:
                block.content = normalize_inline_math(block.content)
            except Exception as e:
                print("Warning: Failed to process text: ", e)
                print("Content: ", block.content)

        if block.type == "table" and block.content:
            try:
                block.content = convert_otsl_to_html(block.content)
                block.content = remove_useless_label(block.content)
            except Exception as e:
                print("Warning: Failed to convert OTSL to HTML: ", e)
                print("Content: ", block.content)
        

    out_blocks: list[ContentBlock] = []
    for block in blocks:
        if block.type == "equation_block":  # drop equation_block anyway
            continue
        if abandon_list and block.type == "list":
            continue
        if abandon_paratext and block.type in PARATEXT_TYPES:
            continue
        out_blocks.append(block)
    return out_blocks
