#!/usr/bin/env python3
"""Unicode-safe Persian cleanup for Markdown. Stdlib only.

Fixes NFC, Arabic ye/kaf, digits, tatweel, duplicate ZWNJ, and می/نمی
prefix spacing. Skips fenced and inline code. Does not rewrite wording.

ponytail: prefix ZWNJ covers می/نمی only. Full suffix/punctuation cleanup
is Virastar; add it only if this script's ceiling shows up in review.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata

ZWNJ = "\u200c"
TATWEEL = "\u0640"
YE_MAP = str.maketrans({"\u064a": "\u06cc", "\u0649": "\u06cc", "\u0643": "\u06a9"})
DIGIT_MAP = str.maketrans(
    "0123456789"
    "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
    "۰۱۲۳۴۵۶۷۸۹"
    "۰۱۲۳۴۵۶۷۸۹",
)
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})")
INLINE_CODE_RE = re.compile(r"`+[^`]*`+")
MI_RE = re.compile(r"(نمی|می)[\u0020\u00a0\u200c]*")
PERSIAN_LETTER = re.compile(r"[\u0600-\u06FF]")


def _cleanup_prose(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.translate(YE_MAP)
    text = text.replace(TATWEEL, "")
    text = re.sub(rf"{ZWNJ}{{2,}}", ZWNJ, text)

    def mi(m: re.Match[str]) -> str:
        end = m.end()
        rest = text[end:]
        if rest and PERSIAN_LETTER.match(rest[0]):
            return m.group(1) + ZWNJ
        return m.group(0)

    text = MI_RE.sub(mi, text)
    text = text.translate(DIGIT_MAP)
    return text


def normalize_markdown(src: str) -> str:
    out: list[str] = []
    fence: str | None = None
    for line in src.splitlines(keepends=True):
        nl = ""
        if line.endswith("\n"):
            line, nl = line[:-1], "\n"
        m = FENCE_RE.match(line)
        if m:
            mark = m.group(2)[0]
            n = len(m.group(2))
            token = mark * n
            if fence is None:
                fence = token
            elif line.strip().startswith(fence):
                fence = None
            out.append(line + nl)
            continue
        if fence is not None:
            out.append(line + nl)
            continue
        parts: list[str] = []
        last = 0
        for cm in INLINE_CODE_RE.finditer(line):
            parts.append(_cleanup_prose(line[last : cm.start()]))
            parts.append(cm.group(0))
            last = cm.end()
        parts.append(_cleanup_prose(line[last:]))
        out.append("".join(parts) + nl)
    return "".join(out)


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("path")
    p.add_argument("-o", "--output", help="write here instead of in place")
    p.add_argument("--check", action="store_true", help="exit 1 if file would change")
    args = p.parse_args(argv)
    raw = open(args.path, encoding="utf-8").read()
    cleaned = normalize_markdown(raw)
    if args.check:
        return 0 if cleaned == raw else 1
    dest = args.output or args.path
    open(dest, "w", encoding="utf-8").write(cleaned)
    return 0


def _selfcheck() -> None:
    src = "فارسي را كمی درست تر مي نويسيم 123 و `code 1`\n```\nمي شود 2\n```\n"
    got = normalize_markdown(src)
    assert "فارسی" in got, got
    assert "کمی" in got, got
    assert "می‌نویسیم" in got, got
    assert "۱۲۳" in got, got
    assert "`code 1`" in got, got
    assert "مي شود 2" in got, got  # fenced code left alone
    print("persian-normalize selfcheck ok")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selfcheck":
        _selfcheck()
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
