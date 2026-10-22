import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"


@dataclass
class Evidence:
    source: str
    title: str
    score: float
    content: str

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "title": self.title,
            "score": round(self.score, 4),
            "content": self.content,
        }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _char_ngrams(text: str, n: int = 2) -> list:
    t = _normalize(text)
    if len(t) < n:
        return [t] if t else []
    return [t[i:i + n] for i in range(len(t) - n + 1)]


class KnowledgeBase:
    """轻量知识库：字符 n-gram 的 TF-IDF + 余弦相似度，无外部依赖。"""

    def __init__(self):
        self.chunks: list[dict] = []
        self._idf: dict[str, float] = {}
        self._load()

    def _load(self):
        raw = []
        for md in sorted(KB_DIR.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            doc_title = ""
            sections = []
            cur_title, cur_body = "", []
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("# "):
                    doc_title = line[2:]
                elif line.startswith("## "):
                    if cur_title or cur_body:
                        sections.append((cur_title, "\n".join(cur_body).strip()))
                    cur_title, cur_body = line[3:], []
                elif line:
                    cur_body.append(line)
            if cur_title or cur_body:
                sections.append((cur_title, "\n".join(cur_body).strip()))
            for sec_title, content in sections:
                if content:
                    raw.append((md.name, sec_title or doc_title, content))

        df = Counter()
        for _, _, content in raw:
            df.update(set(_char_ngrams(content)))
        n_docs = len(raw) or 1
        self._idf = {t: math.log((n_docs + 1) / (c + 1)) + 1 for t, c in df.items()}

        self.chunks = []
        for source, title, content in raw:
            self.chunks.append({
                "source": source,
                "title": title,
                "content": content,
                "vector": self._tfidf_vector(content),
            })

    def _tfidf_vector(self, text: str) -> dict:
        c = Counter(_char_ngrams(text))
        total = len(list(c.elements())) or 1
        return {t: (cnt / total) * self._idf.get(t, 1.0) for t, cnt in c.items()}

    def _cosine(self, v1: dict, v2: dict) -> float:
        common = set(v1) & set(v2)
        dot = sum(v1[t] * v2[t] for t in common)
        n1 = math.sqrt(sum(w * w for w in v1.values())) or 1.0
        n2 = math.sqrt(sum(w * w for w in v2.values())) or 1.0
        return dot / (n1 * n2)

    def search(self, query: str, top_k: int = 6) -> list[Evidence]:
        if not query:
            return []
        qv = self._tfidf_vector(query)
        scored = [
            Evidence(c["source"], c["title"], self._cosine(qv, c["vector"]), c["content"])
            for c in self.chunks
        ]
        scored = [e for e in scored if e.score > 0]
        scored.sort(key=lambda e: e.score, reverse=True)
        return scored[:top_k]


_kb = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
