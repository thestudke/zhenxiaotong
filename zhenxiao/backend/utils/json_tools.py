import json
import re


def try_parse_json(raw: str):
    """按「JSON 解析 → 叙事解析」顺序尝试解析，返回 dict 或 None。"""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
    return None


def repair_json(raw: str):
    """JSON 修复：先复用解析，再尝试去尾逗号、单引号转双引号。"""
    parsed = try_parse_json(raw)
    if parsed:
        return parsed
    if not raw:
        return None
    m = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if not m:
        return None
    fixed = m.group(0)
    fixed = re.sub(r",\s*([}\]])", r"\1", fixed)
    fixed = re.sub(r"'([^']*)'\s*:", r'"\1":', fixed)
    try:
        return json.loads(fixed)
    except Exception:
        return None
