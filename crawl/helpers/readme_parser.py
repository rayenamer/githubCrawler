"""Extract a short human description from a raw README (markdown/HTML/rst)."""

import html
import re

MAX_LENGTH = 300
MIN_LENGTH = 20

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCED_CODE = re.compile(r"^(```|~~~).*?^\1[ \t]*$", re.DOTALL | re.MULTILINE)
_HTML_HEADING = re.compile(r"<h[1-6][^>]*>.*?</h[1-6]>", re.DOTALL | re.IGNORECASE)
_HTML_BLOCK_BREAK = re.compile(r"</?(p|div|br|table|tr|td|ul|ol|li)\b[^>]*>", re.IGNORECASE)
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)|!\[[^\]]*\]\[[^\]]*\]")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)|\[([^\]]*)\]\[[^\]]*\]")
_REF_DEFINITION = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.MULTILINE)
_HTML_TAG = re.compile(r"<[^>]+>")
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|~~)(?=\S)(.+?)(?<=\S)\1")
_INLINE_CODE = re.compile(r"`([^`]*)`")
_URL_ONLY = re.compile(r"^(https?://\S+\s*)+$")
_SETEXT_UNDERLINE = re.compile(r"^\s*(=+|-+)\s*$")
_RULE = re.compile(r"^\s*([-*_=~#+^])(\s*\1){2,}\s*$")
_ATX_HEADING = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
_TABLE_ROW = re.compile(r"^\s*\|")
_LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
_BLOCKQUOTE = re.compile(r"^\s*>\s?")
_ALERT = re.compile(r"\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*", re.IGNORECASE)


def extract_description(readme: str) -> str | None:
    """Return the first prose paragraph of a README, cleaned and truncated.

    Skips titles, badges, images, tables, code, lists and link-only lines.
    Prefers a paragraph of at least MIN_LENGTH chars, falls back to the first
    shorter one, and returns None when the README has no usable prose.
    """
    text = readme.replace("\r\n", "\n")
    text = _COMMENT.sub("", text)
    text = _FENCED_CODE.sub("", text)
    text = _HTML_HEADING.sub("\n\n", text)
    text = _HTML_BLOCK_BREAK.sub("\n\n", text)
    text = _REF_DEFINITION.sub("", text)

    short_fallback = None
    for block in re.split(r"\n\s*\n", text):
        paragraph = _clean_block(block)
        if not paragraph:
            continue
        if len(paragraph) >= MIN_LENGTH:
            return _truncate(paragraph)
        # Keep a short line (e.g. "Hello World!") in case nothing longer exists.
        short_fallback = short_fallback or paragraph
    return short_fallback


def _clean_block(block: str) -> str | None:
    lines = [line for line in block.split("\n") if line.strip()]
    if not lines:
        return None

    first = lines[0]
    if (
        _ATX_HEADING.match(first)
        or _TABLE_ROW.match(first)
        or _LIST_ITEM.match(first)
        or _RULE.match(first)
        or first.startswith(("    ", "\t"))  # indented code block
    ):
        return None
    # Setext heading ("Title\n=====") or rst title with over/underline.
    if any(_SETEXT_UNDERLINE.match(line) for line in lines[1:]):
        return None

    lines = [_BLOCKQUOTE.sub("", line) for line in lines]
    text = " ".join(line.strip() for line in lines)

    text = _ALERT.sub("", text)
    text = _IMAGE.sub("", text)
    text = _LINK.sub(lambda m: m.group(1) or m.group(2) or "", text)
    text = _HTML_TAG.sub("", text)
    text = _INLINE_CODE.sub(r"\1", text)
    text = _EMPHASIS.sub(r"\2", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text or _URL_ONLY.match(text):
        return None
    # Needs actual words, not leftover punctuation from stripped badges.
    if not re.search(r"[A-Za-z]{2,}.*\s.*[A-Za-z]{2,}", text):
        return None
    return text


def _truncate(text: str) -> str:
    if len(text) <= MAX_LENGTH:
        return text
    cut = text[:MAX_LENGTH].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut + "…"
