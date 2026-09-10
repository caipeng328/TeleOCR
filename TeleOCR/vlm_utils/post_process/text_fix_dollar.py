import re

PATTERN = re.compile(r'(?<!\\)(?<!\$)\$(?!\$)')

def replace_double_dollar(text: str) -> str:
    return text.replace("$$", "$")

def normalize_inline_math(text: str) -> str:
    text = replace_double_dollar(text)
    matches = list(PATTERN.finditer(text))

    if len(matches) & 1 or len(matches) == 0:
        return text

    result = []
    last = 0
    n = len(text)

    for i in range(0, len(matches), 2):
        left = matches[i]
        right = matches[i + 1]
        result.append(text[last:left.start()])
        if left.start() > 0 and not text[left.start() - 1].isspace():
            result.append(" ")
        content = text[left.end():right.start()].strip()
        result.append(f"${content}$")
        if (
            right.end() < n
            and not text[right.end()].isspace()
        ):
            result.append(" ")
        last = right.end()
    result.append(text[last:])
    return "".join(result)

