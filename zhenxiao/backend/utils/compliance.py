DISCLAIMER = "以上内容仅用于健康科普和就医参考，不能替代医生诊断、处方或治疗。"

_REPLACEMENTS = [
    ("确诊为", "需要由医生评估是否为"),
    ("一定是", "可能为"),
    ("必须服用", "是否用药需要医生评估"),
    ("剂量是", "具体剂量需要遵医嘱"),
]


def compliance_guard(text: str) -> str:
    """合规处理：替换绝对化/诊断性表达，缺失时追加免责声明。"""
    if not text:
        return text
    for src, dst in _REPLACEMENTS:
        text = text.replace(src, dst)
    if DISCLAIMER not in text:
        text = text.rstrip() + "\n\n" + DISCLAIMER
    return text.strip()
