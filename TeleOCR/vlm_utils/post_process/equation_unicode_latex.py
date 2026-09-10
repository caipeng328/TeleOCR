import re

# =========================
# LaTeX <-> Unicode 映射
# =========================

LATEX_TO_UNICODE = {

    # =========================
    # 比较符号
    # =========================

    r'\geq': '≥',
    r'\leq': '≤',
    r'\neq': '≠',
    r'\approx': '≈',
    r'\equiv': '≡',
    r'\sim': '∼',
    r'\simeq': '≃',
    r'\cong': '≅',
    r'\propto': '∝',
    r'\ll': '≪',
    r'\gg': '≫',
    r'\prec': '≺',
    r'\succ': '≻',
    r'\preceq': '≼',
    r'\succeq': '≽',

    # =========================
    # 基础运算
    # =========================

    r'\times': '×',
    r'\div': '÷',
    r'\pm': '±',
    r'\mp': '∓',
    r'\cdot': '·',
    r'\ast': '∗',
    r'\star': '⋆',
    r'\circ': '∘',
    r'\bullet': '•',
    r'\diamond': '⋄',

    # =========================
    # 集合
    # =========================

    r'\in': '∈',
    r'\notin': '∉',
    r'\ni': '∋',
    r'\subset': '⊂',
    r'\supset': '⊃',
    r'\subseteq': '⊆',
    r'\supseteq': '⊇',
    r'\cup': '∪',
    r'\cap': '∩',
    r'\emptyset': '∅',
    r'\varnothing': '∅',

    # =========================
    # 逻辑
    # =========================

    r'\forall': '∀',
    r'\exists': '∃',
    r'\neg': '¬',
    r'\land': '∧',
    r'\wedge': '∧',
    r'\lor': '∨',
    r'\vee': '∨',
    r'\therefore': '∴',
    r'\because': '∵',

    # =========================
    # 箭头
    # =========================

    r'\to': '→',
    r'\rightarrow': '→',
    r'\leftarrow': '←',
    r'\leftrightarrow': '↔',
    r'\Rightarrow': '⇒',
    r'\Leftarrow': '⇐',
    r'\Leftrightarrow': '⇔',
    r'\mapsto': '↦',
    r'\hookrightarrow': '↪',

    # =========================
    # 微积分 / 分析
    # =========================

    r'\infty': '∞',
    r'\partial': '∂',
    r'\nabla': '∇',
    r'\angle': '∠',
    r'\triangle': '△',
    r'\square': '□',
    r'\perp': '⊥',
    r'\parallel': '∥',
    r'\prime': '′',
    r'\degree': '°',

    # =========================
    # 大型运算符（可选）
    # =========================

    r'\sum': '∑',
    r'\prod': '∏',
    r'\coprod': '∐',
    r'\int': '∫',
    r'\oint': '∮',

    # =========================
    # 希腊字母（小写）
    # =========================

    r'\alpha': 'α',
    r'\beta': 'β',
    r'\gamma': 'γ',
    r'\delta': 'δ',
    r'\epsilon': 'ε',
    r'\varepsilon': 'ϵ',
    r'\zeta': 'ζ',
    r'\eta': 'η',
    r'\theta': 'θ',
    r'\vartheta': 'ϑ',
    r'\iota': 'ι',
    r'\kappa': 'κ',
    r'\lambda': 'λ',
    r'\mu': 'μ',
    r'\nu': 'ν',
    r'\xi': 'ξ',
    r'\pi': 'π',
    r'\varpi': 'ϖ',
    r'\rho': 'ρ',
    r'\varrho': 'ϱ',
    r'\sigma': 'σ',
    r'\varsigma': 'ς',
    r'\tau': 'τ',
    r'\upsilon': 'υ',
    r'\phi': 'φ',
    r'\varphi': 'ϕ',
    r'\chi': 'χ',
    r'\psi': 'ψ',
    r'\omega': 'ω',

    # =========================
    # 希腊字母（大写）
    # =========================

    r'\Gamma': 'Γ',
    r'\Delta': 'Δ',
    r'\Theta': 'Θ',
    r'\Lambda': 'Λ',
    r'\Xi': 'Ξ',
    r'\Pi': 'Π',
    r'\Sigma': 'Σ',
    r'\Upsilon': 'Υ',
    r'\Phi': 'Φ',
    r'\Psi': 'Ψ',
    r'\Omega': 'Ω',

    # =========================
    # 特殊符号
    # =========================

    r'\aleph': 'ℵ',
    r'\hbar': 'ℏ',
    r'\ell': 'ℓ',
    r'\Re': 'ℜ',
    r'\Im': 'ℑ',
    r'\wp': '℘',
    r'\mho': '℧',

    # =========================
    # 其它
    # =========================

    r'\copyright': '©',
    r'\registered': '®',
    r'\dagger': '†',
    r'\ddagger': '‡',
}
# 反向映射
UNICODE_TO_LATEX = {
    v: f'{k} ' for k, v in LATEX_TO_UNICODE.items()
}

# 避免 \to 抢先替换 \rightarrow
LATEX_PATTERNS = sorted(
    LATEX_TO_UNICODE.keys(),
    key=len,
    reverse=True
)

# =========================
# latex -> unicode
# =========================

def latex_to_unicode(text: str) -> str:
    for latex in LATEX_PATTERNS:
        unicode_char = LATEX_TO_UNICODE[latex]
        text = re.sub(
            re.escape(latex) + r'(?![A-Za-z])',
            unicode_char,
            text
        )
    return text


# =========================
# unicode -> latex
# =========================

def unicode_to_latex(raw_text: str) -> str:
    text = raw_text
    for unicode_char, latex in UNICODE_TO_LATEX.items():
        text = text.replace(unicode_char, latex)
    flag = raw_text != text
    return text


# =========================
# 测试
# =========================

if __name__ == "__main__":

    latex_text = r"""
    a ∞~ b,\quad
    x \neq y,\quad
    A \subseteq B,\quad
    x \rightarrow y
    """

    unicode_text = latex_to_unicode(latex_text)

    print("latex -> unicode")
    print(unicode_text)

    print()

    restored = unicode_to_latex(unicode_text)

    print("unicode -> latex")
    print(restored)