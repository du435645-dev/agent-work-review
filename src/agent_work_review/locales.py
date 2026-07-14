from __future__ import annotations


SUMMARY_TEXT = {
    "en": {
        "title": "Structured Work Review",
        "executive": "Executive summary",
        "background": "Background",
        "content": "What was delivered",
        "impact": "Impact",
        "next": "Next steps",
        "default_background": "This work was completed in the {workspace} workstream to move the related objective forward.",
        "default_output": "Produced a concrete deliverable or reusable artifact.",
        "default_decision": "Captured a clear decision and the reasoning behind it.",
        "default_progress": "Completed meaningful progress toward a final deliverable or decision.",
        "default_next": "Continue validation and refine the material when the workstream advances.",
    },
    "zh": {
        "title": "\u7ed3\u6784\u5316\u5de5\u4f5c\u603b\u7ed3",
        "executive": "\u603b\u4f53\u603b\u7ed3",
        "background": "\u4ea7\u51fa\u7684\u80cc\u666f",
        "content": "\u4ea7\u51fa\u7684\u5185\u5bb9",
        "impact": "\u4ea7\u51fa\u7684\u6210\u6548",
        "next": "\u540e\u7eed\u8ba1\u5212",
        "default_background": "\u5728 {workspace} \u5de5\u4f5c\u7ebf\u4e2d\uff0c\u4e3a\u63a8\u8fdb\u76f8\u5173\u76ee\u6807\u5f00\u5c55\u4e86\u672c\u8f6e\u5de5\u4f5c\u3002",
        "default_output": "\u5f62\u6210\u4e86\u660e\u786e\u4ea4\u4ed8\u6216\u53ef\u590d\u7528\u4ea7\u7269\u3002",
        "default_decision": "\u6c89\u6dc0\u4e86\u660e\u786e\u51b3\u7b56\u53ca\u5176\u53d6\u820d\u4f9d\u636e\u3002",
        "default_progress": "\u5b8c\u6210\u4e86\u9762\u5411\u6700\u7ec8\u4ea7\u51fa\u6216\u51b3\u7b56\u7684\u9636\u6bb5\u6027\u63a8\u8fdb\u3002",
        "default_next": "\u968f\u5de5\u4f5c\u7ebf\u63a8\u8fdb\u7ee7\u7eed\u8865\u5145\u9a8c\u8bc1\u5e76\u5b8c\u5584\u6750\u6599\u3002",
    },
}

PRESENTATION_LABELS = {
    "en": {
        "review": "Work Review",
        "overview": "Overview",
        "background": "Background",
        "content": "What was delivered",
        "impact": "Impact",
        "next": "Next steps",
        "sources": "Sources",
        "close": "Evidence first. Then make the work visible.",
        "hint": "Arrow keys / swipe to navigate - Esc for index",
    },
    "zh": {
        "review": "\u5de5\u4f5c\u603b\u7ed3",
        "overview": "\u603b\u89c8",
        "background": "\u80cc\u666f",
        "content": "\u4ea7\u51fa\u5185\u5bb9",
        "impact": "\u6210\u6548",
        "next": "\u540e\u7eed\u8ba1\u5212",
        "sources": "\u6765\u6e90",
        "close": "\u5148\u6c89\u6dc0\u8bc1\u636e\uff0c\u518d\u8ba9\u5de5\u4f5c\u88ab\u770b\u89c1\u3002",
        "hint": "\u65b9\u5411\u952e / \u6ed1\u52a8\u7ffb\u9875 - Esc \u67e5\u770b\u7d22\u5f15",
    },
}

QUANTIFIED_TOKENS = ("%", "+", "increase", "decrease", "\u63d0\u5347", "\u4e0b\u964d", "\u589e\u957f")
QUANTIFIED_PATTERN = r"(?<![\w])\d+(?:,\d{3})*(?:\.\d+)?\s*(?:reports?|tests?|hours?|days?|items?|\u4efd|\u4e2a|\u6b21|\u5c0f\u65f6|\u5929|\u9879)"
