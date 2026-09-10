import re


def normalize_latex_spaces(text: str) -> str:

    # 合并连续空格
    text = re.sub(r"\s+", " ", text)

    n = len(text)
    i = 0
    out = []

    while i < n:

        # 非空格直接输出
        if text[i] != " ":
            out.append(text[i])
            i += 1
            continue

        keep = False

        if i > 0 and text[i - 1] == "\\":
            keep = True

        else:

            # ---------- 规则1 ----------
            # 判断是否为 \command
            #
            # \times x
            #        ^
            #
            if i + 1 < n and text[i + 1].isalnum():
                j = i - 1

                while j >= 0 and text[j].isalpha():
                    j -= 1

                if (
                    j >= 0
                    and text[j] == "\\"
                    and j + 1 < i - 1
                ):
                    keep = True

        if keep:
            out.append(" ")

        i += 1

    return "".join(out)


if __name__ == "__main__":

    latex = r"""$$\left\{ \ \begin{array} { l l } { h ^ { 21 \ 2 } ( x ) \in \left[ 0 , 6 \right] } \\ { f ^ { 2 } ( x ) = 1 0 - h ^ { 2 } ( x ) \times wq \in \left[ 4 , 1 0 \right] } \end{array} \right. \Rightarrow f ( x ) \in \left[ 2 , \sqrt { 1 0 } \right] ;$$"""

    print(normalize_latex_spaces(latex))
