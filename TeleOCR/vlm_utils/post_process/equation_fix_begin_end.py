import re


KNOWN_ENVS = {
    "align",
    "align*",
    "aligned",
    "alignedat",
    "array",
    "bmatrix",
    "Bmatrix",
    "pmatrix",
    "vmatrix",
    "Vmatrix",
    "matrix",
    "smallmatrix",
    "cases",
    "dcases",
    "rcases",
    "equation",
    "equation*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "split",
}


TOKEN_PATTERN = re.compile(
    r"\\begin\s*\{([^{}]+)\}"
    r"|\\end\s*\{([^{}]+)\}"
)


def check_begin_end(latex: str) -> bool:
    """
    检查 begin/end 是否严格匹配
    """

    stack = []

    for m in TOKEN_PATTERN.finditer(latex):

        begin_env = m.group(1)
        end_env = m.group(2)

        if begin_env is not None:

            if begin_env in KNOWN_ENVS:
                stack.append(begin_env)

        else:

            if end_env not in KNOWN_ENVS:
                continue

            if not stack:
                return False

            if stack[-1] != end_env:
                return False

            stack.pop()

    return len(stack) == 0


def _insert_before_math_end(
    text: str,
    missing: str,
) -> str:
    patterns = [
        r"\$\$\s*$",
        r"\\\]\s*$",
        r"\\end\{equation\*?\}\s*$",
        r"\\end\{align\*?\}\s*$",
    ]

    for pattern in patterns:
        m = re.search(pattern, text)
        if m:
            return (
                text[:m.start()]
                + missing
                + text[m.start():]
            )

    return text + missing


def try_fix_begin_end(
    latex: str,
) -> str:
    """
    自动修复 begin/end
    """

    stack = []

    result = []

    last = 0

    for m in TOKEN_PATTERN.finditer(latex):

        result.append(
            latex[last:m.start()]
        )

        begin_env = m.group(1)
        end_env = m.group(2)

        token = m.group(0)

        if begin_env is not None:

            result.append(token)

            if begin_env in KNOWN_ENVS:
                stack.append(begin_env)

        else:

            if end_env not in KNOWN_ENVS:
                result.append(token)

            else:

                #
                # 正常匹配
                #
                if stack and stack[-1] == end_env:

                    stack.pop()

                    result.append(token)

                #
                # 交叉嵌套
                #
                elif end_env in stack:

                    while stack and stack[-1] != end_env:

                        missing_end = stack.pop()

                        result.append(
                            f"\\end{{{missing_end}}}"
                        )

                    stack.pop()

                    result.append(token)

                #
                # 孤立 end
                #
                else:

                    result.append(token)

        last = m.end()

    result.append(latex[last:])

    fixed = "".join(result)

    #
    # 补齐剩余 begin
    #
    if stack:

        missing = "".join(
            f"\\end{{{env}}}"
            for env in reversed(stack)
        )

        fixed = _insert_before_math_end(
            fixed,
            missing,
        )

    return fixed


if __name__ == "__main__":

    tests = [

        #
        # 正常
        #
        r"$$\begin{align}a+b\end{align}$$",

        #
        # 缺少 end
        #
        r'''$$\begin{align}a+b
        $$''',

        #
        # 双重嵌套缺 end
        #
        r"$$\begin{align}\begin{bmatrix}a&b$$",

        #
        # 交叉嵌套
        #
        r"$$\begin{align}\begin{bmatrix}a&b    21212  \end{align}\end{align}  21121$$",

        #
        # 数学块
        #
        r"$$\begin{align*}\begin{bmatrix}1&0\\0&1$$",

        #
        # 已经正确
        #
        r"$$\begin{align*}\begin{bmatrix}1&0\\0&1\end{bmatrix}\end{align*}$$",

        #
        # 孤立 end
        #
        r"""$$\begin{align*}\begin{bmatrix}1&0&0\\ \ell&1&0\\ m&0&1\end{bmatrix}^n,\qquad\begin{bmatrix}1&0&0\\ \ell&1&0\\ m&0&1^{-1},\qquad\begin{bmatrix}1&0&0\\ \ell&1&0\\ 0&m&1\end{bmatrix}^{-1}.$$"""

    ]

    for i, t in enumerate(tests, 1):

        print("=" * 80)
        print(f"CASE {i}")
        print("-" * 80)

        print("INPUT:")
        print(t)

        print()

        print("VALID:")
        print(check_begin_end(t))

        print()

        fixed = try_fix_begin_end(t)

        print("OUTPUT:")
        print(fixed)

        print()

        print("VALID AFTER FIX:")
        print(check_begin_end(fixed))

        print()