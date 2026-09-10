import re

def move_tail_label_after_dollars(text: str) -> str:
    pattern = re.compile(
        r'^(.*?)'
        r'(?<!\\eqno)'
        r'(?<!\\eqno )'
        r'(?<!\\eqno  )'
        r'(?<!\\eqno   )'
        r'\s*'
        r'(\([A-Za-z0-9][A-Za-z0-9.\-]*\))'
        r'(\s*\$\$\s*)$'
    )

    m = pattern.search(text)
    if not m:
        return text

    prefix = m.group(1)
    label = m.group(2)

    if not prefix.startswith("$$"):
        return text

    body = prefix[2:].rstrip()

    return f"${body}$ {label}"

def fix_tail_tag(text: str) -> str:

    pattern = re.compile(
        r'(?<!\\)tag\s*\{([^{}]*)\}(?=\s*\$\$\s*$)'
    )
    return pattern.sub(
        r'\\tag{\1}',
        text,
    )

def wrap_with_double_dollar(content: str) -> str:
    content = content.replace("$", "").strip()
    content = move_tail_label_after_dollars(f"$${content}$$")
    content = fix_tail_tag(content)
    return content


if __name__ == "__main__":
    tests = [
        "$$E=mc^2(5.3.4-1)$$",
        "$$E=mc^2 (1-2)$$",
        "$$E=mc^2(101.2)$$",
        "$$E=mc^2(A-2)$$",
        "$$E=mc^2(.a-1)$$",
        "$$E=mc^2( A - 2 )$$",
        "$$E=mc^2\\eqno(1-2)$$",
        "$$E=mc^2\\eqno (1-2)$$",
        "$$E=mc^2\\eqno   (1-2)$$",
        "$$12. E=mc^2$$",
        "$$2121. E=mc^2$$",
        "$$1) E=mc^2$$",
        "$$12345) x+y=z$$",
        
        "$$12345) x+y=z \\tag{sa.sas}$$",
    ]

    for t in tests:
        print("IN :", t)
        print("OUT:", wrap_with_double_dollar(t))
        print()