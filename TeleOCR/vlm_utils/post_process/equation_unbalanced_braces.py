def try_fix_unbalanced_braces(latex_formula: str, debug: bool = False):
    stack = []  # 存储左括号的索引
    unmatched = set()  # 存储不匹配括号的索引
    i = 0

    while i < len(latex_formula):
        # 检查是否是转义的花括号
        if latex_formula[i] in ['{', '}']:
            # 计算前面连续的反斜杠数量
            backslash_count = 0
            j = i - 1
            while j >= 0 and latex_formula[j] == '\\':
                backslash_count += 1
                j -= 1

            # 如果前面有奇数个反斜杠，则该花括号是转义的，不参与匹配
            if backslash_count % 2 == 1:
                i += 1
                continue

            # 否则，该花括号参与匹配
            if latex_formula[i] == '{':
                stack.append(i)
            else:  # latex_formula[i] == '}'
                if stack:  # 有对应的左括号
                    stack.pop()
                else:  # 没有对应的左括号
                    unmatched.add(i)

        i += 1

    # 所有未匹配的左括号
    unmatched.update(stack)

    # 构建新字符串，删除不匹配的括号
    return ''.join(char for i, char in enumerate(latex_formula) if i not in unmatched)