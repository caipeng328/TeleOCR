import re


def escape_latex_special_chars(raw_text: str) -> str:
    text = raw_text
    special_chars = [
        '%'
    ]

    for char in special_chars:

        # 匹配：前面不是反斜杠的特殊字符
        pattern = rf'(?<!\\){re.escape(char)}'

        text = re.sub(
            pattern,
            rf'\\{char}',
            text
        )

    return text


# =========================
# 测试
# =========================

if __name__ == "__main__":

    s = r"""
    50% of x_1 & x_2
    already escaped: \%
    #test
    {abc}
    """

    print("原始：")
    print(s)

    print()

    fixed = escape_latex_special_chars(s)

    print("修复后：")
    print(fixed)