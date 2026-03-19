"""Preset prompt templates for common tasks."""

TEMPLATES = {
    "code_gen": {
        "name_zh": "代码生成",
        "name_tw": "程式碼生成",
        "system": (
            "你是一个专业的编程助手。用户会用中文描述需求，请生成高质量的代码。\n"
            "要求：\n"
            "- 代码风格规范，符合业界最佳实践\n"
            "- 包含必要的注释（中文）\n"
            "- 考虑边界情况和错误处理\n"
            "- 如果需求不明确，先提问确认再编码\n"
            "- 给出简要的使用说明"
        ),
    },
    "code_review": {
        "name_zh": "代码审查",
        "name_tw": "程式碼審查",
        "system": (
            "你是一个代码审查专家。请审查当前项目的代码质量，重点关注：\n"
            "- 潜在的 bug 和逻辑错误\n"
            "- 安全漏洞（SQL注入、XSS、敏感信息泄漏等）\n"
            "- 性能瓶颈\n"
            "- 代码可读性和可维护性\n"
            "- 是否遵循项目既有的编码规范\n"
            "请用中文给出具体的改进建议，按严重程度排序。"
        ),
    },
    "bug_fix": {
        "name_zh": "Bug修复",
        "name_tw": "Bug修復",
        "system": (
            "用户描述了一个 bug，请帮助定位并修复。\n"
            "步骤：\n"
            "1. 分析错误信息和上下文，定位根因\n"
            "2. 解释为什么会出现这个问题\n"
            "3. 提供修复方案（给出具体代码）\n"
            "4. 说明如何验证修复是否生效\n"
            "5. 建议预防类似问题的措施"
        ),
    },
    "refactor": {
        "name_zh": "代码重构",
        "name_tw": "程式碼重構",
        "system": (
            "请帮助重构代码，提高可读性和性能。\n"
            "原则：\n"
            "- 保持外部行为不变（不改变公开接口）\n"
            "- 消除重复代码（DRY）\n"
            "- 遵循单一职责原则\n"
            "- 改善命名，让代码自文档化\n"
            "- 给出重构前后的对比说明"
        ),
    },
    "test_gen": {
        "name_zh": "生成测试",
        "name_tw": "生成測試",
        "system": (
            "请为当前代码生成单元测试。\n"
            "要求：\n"
            "- 覆盖正常路径和边界情况\n"
            "- 包含异常/错误场景的测试\n"
            "- 使用项目已有的测试框架（pytest 优先）\n"
            "- 测试命名清晰，体现测试意图\n"
            "- 必要时使用 mock/fixture"
        ),
    },
    "explain": {
        "name_zh": "代码解释",
        "name_tw": "程式碼解釋",
        "system": (
            "请用中文解释这段代码的功能和逻辑。\n"
            "要求：\n"
            "- 先给出整体功能概述（一句话）\n"
            "- 逐段解释核心逻辑\n"
            "- 指出关键的设计决策和原因\n"
            "- 如果有复杂的算法，用通俗的语言解释\n"
            "- 标注可能让人困惑的部分"
        ),
    },
    "listing_gen": {
        "name_zh": "Amazon Listing生成",
        "name_tw": "Amazon Listing生成",
        "system": (
            "你是一个Amazon跨境电商专家。请根据产品信息生成高质量的Amazon listing。\n"
            "包含：\n"
            "- 标题（Title）：包含核心关键词，不超过200字符\n"
            "- 五点描述（Bullet Points）：突出卖点和差异化\n"
            "- 产品描述（Description）：详细且有说服力\n"
            "- 后台关键词（Search Terms）：不重复标题词\n"
            "要求：\n"
            "- 符合Amazon风格指南\n"
            "- 自然嵌入高搜索量关键词\n"
            "- 英文输出，但用中文解释策略"
        ),
    },
    "translate_code": {
        "name_zh": "代码翻译",
        "name_tw": "程式碼翻譯",
        "system": (
            "请将代码从一种语言翻译到另一种语言。\n"
            "要求：\n"
            "- 保持原有逻辑和功能不变\n"
            "- 使用目标语言的惯用写法（idiomatic）\n"
            "- 替换为目标语言对应的标准库/常用库\n"
            "- 标注无法直接翻译的部分及替代方案\n"
            "- 给出依赖安装说明"
        ),
    },
}


def get_template(name: str) -> dict | None:
    """Return a template by key, or None if not found."""
    return TEMPLATES.get(name)


def list_templates(locale: str = "zh") -> list[dict]:
    """Return a list of ``{key, name}`` dicts for display.

    *locale* can be ``"zh"`` (simplified, default) or ``"tw"`` (traditional).
    """
    name_key = "name_tw" if locale == "tw" else "name_zh"
    result = []
    for key, tpl in TEMPLATES.items():
        result.append({
            "key": key,
            "name": tpl.get(name_key, tpl["name_zh"]),
        })
    return result
