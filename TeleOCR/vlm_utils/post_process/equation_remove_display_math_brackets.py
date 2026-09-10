import re


def remove_math_brackets(text: str) -> str:
    text = re.sub(
        r"^(\$\$)?\s*\\[\[\(]\s*",
        lambda m: m.group(1) or "",
        text,
    )

    text = re.sub(
        r"\s*\\[\]\)]\s*(\$\$)?$",
        lambda m: m.group(1) or "",
        text,
    )

    return text

# print(remove_math_brackets(r"\[\frac{1}{2}\]"))
# # \frac{1}{2}

# print(remove_math_brackets(r"\(\frac{1}{2}\)"))
# # \frac{1}{2}

# print(remove_math_brackets(r"$$\[\frac{1}{2}\]$$"))
# # $$\frac{1}{2}$$

# print(remove_math_brackets(r"$$\(\frac{1}{2}\)$$"))
# # $$\frac{1}{2}$$

# print(remove_math_brackets(r"\[\frac{\[a\]}{2}\]"))
# # \frac{\[a\]}{2}