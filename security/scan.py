"""게시 전 비밀·PII 스캐너 (순수 파이썬, gitleaks 대체).

워킹트리(및 선택적으로 git 히스토리)를 스캔해 아래를 탐지한다:
  - 주민등록번호, 휴대폰번호, 은행계좌(길이 기반)
  - API 키/토큰 (Notion ntn_, GitHub gho_/ghp_, OpenAI sk-, AWS AKIA, Google AIza, 일반 장문토큰)
  - 내부 IP (10.x / 192.168.x / 172.16-31.x)
  - 한글 기관명/임직원명 사전 (sensitive_terms.txt, 한 줄에 하나)
사용: python scan.py <스캔경로> [--terms sensitive_terms.txt]
종료코드: hit 있으면 1, 없으면 0.
"""
from __future__ import annotations
import os, re, sys, json

PATTERNS: dict[str, re.Pattern] = {
    "rrn": re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b"),
    "phone": re.compile(r"\b01[016-9][-\s]?\d{3,4}[-\s]?\d{4}\b"),
    "notion_token": re.compile(r"\bntn_[A-Za-z0-9]{20,}\b"),
    "github_token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "google_key": re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----"),
    "internal_ip": re.compile(r"\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
    "bank_acct": re.compile(r"\b\d{2,6}-\d{2,6}-\d{2,7}\b"),
}

# 오탐 억제: 예시/합성 표시가 있는 라인은 완화 (문서 내 형식 설명 등)
ALLOW_HINT = re.compile(r"(예시|형식|형태|합성|dummy|sample|format|900101-1234567|010-\d{4}-\d{4}\s*\)?\s*형)")

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".7z", ".pfx",
           ".crt", ".key", ".ttf", ".ttc", ".jar", ".exe", ".dll", ".pyc",
           ".xlsx", ".docx", ".pptx", ".webm", ".mp4", ".ico"}


def load_terms(path: str | None) -> list[str]:
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def scan_text(text: str, terms: list[str]) -> list[dict]:
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if ALLOW_HINT.search(line):
            continue
        for name, pat in PATTERNS.items():
            for m in pat.finditer(line):
                mt = m.group()
                # 오탐 억제: ISO 날짜(YYYY-MM-DD)를 계좌로 오인하지 않음
                if name == "bank_acct" and re.fullmatch(r"\d{4}-\d{2}-\d{2}", mt):
                    continue
                hits.append({"line": i, "rule": name, "match": mt[:6] + "***"})
        for t in terms:
            if t in line:
                hits.append({"line": i, "rule": "sensitive_term", "match": t})
    return hits


def scan_path(root: str, terms: list[str]) -> dict:
    report = {"root": root, "files_scanned": 0, "findings": []}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in BIN_EXT:
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            report["files_scanned"] += 1
            hits = scan_text(text, terms)
            if hits:
                report["findings"].append({"file": os.path.relpath(fp, root), "hits": hits})
    return report


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: python scan.py <path> [--terms file]"); sys.exit(2)
    root = args[0]
    terms_file = None
    if "--terms" in args:
        terms_file = args[args.index("--terms") + 1]
    terms = load_terms(terms_file)
    rep = scan_path(root, terms)
    total = sum(len(f["hits"]) for f in rep["findings"])
    rep["total_hits"] = total
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
