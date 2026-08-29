from __future__ import annotations

import html
import posixpath
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import bleach
import mistune
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import TextLexer, get_lexer_by_name
from pygments.util import ClassNotFound


@dataclass(frozen=True)
class TocEntry:
    level: int
    identifier: str
    title: str


@dataclass(frozen=True)
class RenderedMarkdown:
    html: str
    toc: list[TocEntry]


def slugify(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", "", value))
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("’", "").replace("‘", "").replace("'", "")
    value = re.sub(r"[^\w\-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "section"


def preprocess_markdown(markdown: str) -> str:
    """Normalize cp-algorithms and MkDocs extensions for Mistune."""
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    markdown = re.sub(
        r"^```\{\.([A-Za-z0-9_+\-]+)(?:\s+[^}]*)?\}\s*$",
        r"```\1",
        markdown,
        flags=re.MULTILINE,
    )

    source_lines = markdown.splitlines()
    expanded: list[str] = []
    index = 0
    default_titles = {
        "info": "Ma’lumot",
        "example": "Misol",
        "note": "Izoh",
        "warning": "Ogohlantirish",
        "tip": "Maslahat",
        "success": "Muvaffaqiyat",
        "danger": "Muhim ogohlantirish",
    }
    while index < len(source_lines):
        match = re.match(
            r'^(?:!!!|\?\?\?)\s+([A-Za-z0-9_-]+)(?:\s+["\'](.*)["\'])?\s*$',
            source_lines[index],
        )
        if not match:
            expanded.append(source_lines[index])
            index += 1
            continue
        kind, explicit_title = match.groups()
        title = explicit_title or default_titles.get(kind.casefold(), kind.capitalize())
        expanded.extend([f'> **{title}**', ">"])
        index += 1
        content: list[str] = []
        while index < len(source_lines):
            candidate = source_lines[index]
            if not candidate.strip():
                content.append("")
                index += 1
                continue
            if candidate.startswith("    "):
                content.append(candidate[4:])
                index += 1
                continue
            if candidate.startswith("\t"):
                content.append(candidate[1:])
                index += 1
                continue
            break
        while content and not content[-1].strip():
            content.pop()
        for line in content:
            expanded.append(">" if not line else f"> {line}")
        expanded.append("")

    result: list[str] = []
    for line in expanded:
        named_anchor = re.match(
            r'^(#{1,6})\s+<a\s+name=["\']([^"\']+)["\']></a>(.+?)\s*$', line
        )
        if named_anchor:
            hashes, identifier, title = named_anchor.groups()
            cleaned_title = title.strip()
            if identifier != slugify(cleaned_title):
                result.append(
                    f'<a id="{html.escape(identifier, quote=True)}" class="anchor-alias"></a>'
                )
            result.append(f"{hashes} {cleaned_title}")
            continue

        attribute_heading = re.match(r"^(#{1,6})\s+(.+?)\s+\{([^{}]+)\}\s*$", line)
        if attribute_heading:
            hashes, title, attributes = attribute_heading.groups()
            aliases: list[str] = []
            explicit = re.search(r"(?:^|\s)#([A-Za-z0-9_\-]+)(?:\s|$)", attributes)
            if explicit:
                aliases.append(explicit.group(1))
            # data-toc-label controls only the MkDocs TOC label. The visible
            # heading receives its own stable slug, so a second alias is both
            # unnecessary and capable of producing duplicate IDs.
            heading_identifier = slugify(re.sub(r"<[^>]+>", "", title))
            for identifier in aliases:
                if identifier == heading_identifier:
                    continue
                result.append(
                    f'<a id="{html.escape(identifier, quote=True)}" class="anchor-alias"></a>'
                )
            result.append(f"{hashes} {title}")
            continue
        result.append(line)
    return "\n".join(result) + "\n"


def protect_math(markdown: str) -> tuple[str, dict[str, tuple[str, str]]]:
    replacements: dict[str, tuple[str, str]] = {}
    counter = 0

    def store(raw: str, *, display: bool) -> str:
        nonlocal counter
        token = f"CPUZMATH{counter:06d}TOKEN"
        counter += 1
        css_class = "math-display" if display else "math-inline"
        replacement = f'<span class="{css_class}">{html.escape(raw, quote=False)}</span>'
        replacements[token] = (replacement, raw)
        return token

    def process_text(segment: str) -> str:
        inline_code: dict[str, str] = {}
        code_counter = 0

        def protect_code(match: re.Match[str]) -> str:
            nonlocal code_counter
            token = f"CPUZINLINECODE{code_counter:06d}TOKEN"
            code_counter += 1
            inline_code[token] = match.group(0)
            return token

        segment = re.sub(r"(`+)([^\n]*?)\1", protect_code, segment)
        segment = re.sub(
            r"(?<!\\)\$\$(.+?)(?<!\\)\$\$",
            lambda match: store(match.group(0), display=True),
            segment,
            flags=re.DOTALL,
        )
        segment = re.sub(
            r"\\\[(.+?)\\\]",
            lambda match: store(match.group(0), display=True),
            segment,
            flags=re.DOTALL,
        )
        segment = re.sub(
            r"\\\((.+?)\\\)",
            lambda match: store(match.group(0), display=False),
            segment,
        )
        segment = re.sub(
            r"(?<!\\)(?<!\$)\$(?!\$)([^\n]*?)(?<!\\)\$(?!\$)",
            lambda match: store(match.group(0), display=False),
            segment,
        )
        for token, original in inline_code.items():
            segment = segment.replace(token, original)
        return segment

    fence = re.compile(r"(^\s*(`{3,}|~{3,})[^\n]*\n.*?^\s*\2\s*$)", re.MULTILINE | re.DOTALL)
    parts = fence.split(markdown)
    # re.split with a nested capture includes marker captures. Use a manual scan
    # instead to avoid processing fenced code.
    output: list[str] = []
    cursor = 0
    opener = re.compile(r"^\s*(`{3,}|~{3,})[^\n]*\n", re.MULTILINE)
    while True:
        match = opener.search(markdown, cursor)
        if not match:
            output.append(process_text(markdown[cursor:]))
            break
        output.append(process_text(markdown[cursor : match.start()]))
        marker = match.group(1)
        closing = re.compile(rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*$", re.MULTILINE)
        close_match = closing.search(markdown, match.end())
        if not close_match:
            output.append(markdown[match.start() :])
            break
        end = close_match.end()
        output.append(markdown[match.start() : end])
        cursor = end
    return "".join(output), replacements


LANGUAGE_LABELS = {
    "cpp": "C++",
    "c++": "C++",
    "cxx": "C++",
    "python": "Python",
    "py": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "text": "Matn",
    "plaintext": "Matn",
    "bash": "Shell",
    "sh": "Shell",
}


class SiteRenderer(mistune.HTMLRenderer):
    def __init__(self, math_replacements: dict[str, tuple[str, str]]) -> None:
        super().__init__(escape=False)
        self.math_replacements = math_replacements
        self.code_replacements: dict[str, str] = {}
        self.used_ids: dict[str, int] = {}
        self.toc: list[TocEntry] = []

    def _restore_plain_math(self, value: str) -> str:
        for token, (_, raw) in self.math_replacements.items():
            value = value.replace(token, raw)
        return value

    def heading(self, text: str, level: int, **attrs: object) -> str:
        plain = html.unescape(re.sub(r"<[^>]+>", "", text))
        plain = self._restore_plain_math(plain).strip()
        base = slugify(plain)
        count = self.used_ids.get(base, 0)
        self.used_ids[base] = count + 1
        identifier = base if count == 0 else f"{base}-{count + 1}"
        if 2 <= level <= 4:
            self.toc.append(TocEntry(level=level, identifier=identifier, title=plain))
        return (
            f'<h{level} id="{html.escape(identifier, quote=True)}">'
            f'<a class="heading-anchor" href="#{html.escape(identifier, quote=True)}" '
            f'aria-label="Ushbu bo‘limga havola">#</a>{text}</h{level}>\n'
        )

    def block_code(self, code: str, info: str | None = None) -> str:
        language = ""
        if info:
            language = info.strip().split(None, 1)[0].strip("{}.")
        lexer = TextLexer(stripall=False)
        if language:
            try:
                lexer = get_lexer_by_name(language, stripall=False)
            except ClassNotFound:
                lexer = TextLexer(stripall=False)
        highlighted = highlight(code, lexer, HtmlFormatter(nowrap=True))
        label = LANGUAGE_LABELS.get(language.casefold(), language or "Kod")
        language_class = re.sub(r"[^A-Za-z0-9_+\-]", "", language) or "text"
        block = (
            f'<div class="code-block" data-language="{html.escape(language_class, quote=True)}">'
            '<div class="code-toolbar">'
            f'<span>{html.escape(label)}</span>'
            '<button class="copy-code" type="button" aria-label="Kodni nusxalash">Nusxalash</button>'
            '</div>'
            f'<pre><code class="language-{html.escape(language_class, quote=True)}">{highlighted}</code></pre>'
            '</div>\n'
        )
        # Pygments can produce tens of thousands of nested span tokens in a
        # single article. Feeding those trusted, generated spans through
        # html5lib makes sanitization pathologically slow. Sanitize all
        # contributor-controlled HTML first, then restore this escaped block.
        token = f"CPUZCODE{len(self.code_replacements):06d}TOKEN"
        self.code_replacements[token] = block
        return token + "\n"

    def codespan(self, text: str) -> str:
        return f"<code>{html.escape(text, quote=False)}</code>"


ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "button",
    "caption",
    "code",
    "col",
    "colgroup",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "img",
    "kbd",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "s",
    "small",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
}


def allowed_attribute(tag: str, name: str, value: str) -> bool:
    if name.startswith("on"):
        return False
    if name in {"class", "id", "title", "role", "aria-label", "aria-hidden"}:
        return True
    if name.startswith("data-"):
        return True
    if tag == "a" and name in {"href", "rel", "target", "name"}:
        return True
    if tag in {"img"} and name in {"src", "alt", "width", "height", "loading", "decoding"}:
        return True
    if tag in {"td", "th"} and name in {"colspan", "rowspan", "scope"}:
        return True
    if tag == "button" and name == "type":
        return True
    if tag == "details" and name == "open":
        return True
    return False


def sanitize_html(rendered: str) -> str:
    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=allowed_attribute,
        protocols={"http", "https", "mailto"},
        strip=True,
        strip_comments=True,
    )
    cleaned = re.sub(
        r'<a href="(https?://[^"]+)"(?![^>]*\brel=)([^>]*)>',
        r'<a href="\1" target="_blank" rel="noopener noreferrer"\2>',
        cleaned,
    )
    return cleaned


def rewrite_article_links(
    rendered: str,
    *,
    article: dict[str, Any],
    article_by_path: dict[str, dict[str, Any]],
) -> str:
    source_dir = posixpath.dirname(article["path"])
    route_dir = posixpath.dirname(article["route"])

    def replace(match: re.Match[str]) -> str:
        original = html.unescape(match.group(1))
        parts = urlsplit(original)
        if parts.scheme or parts.netloc or not parts.path or not parts.path.lower().endswith(".md"):
            return match.group(0)
        target_source = posixpath.normpath(posixpath.join(source_dir, unquote(parts.path)))
        target = article_by_path.get(target_source)
        if target is None:
            return match.group(0)
        target_route = posixpath.relpath(target["route"], start=route_dir)
        if parts.query:
            target_route += "?" + parts.query
        if parts.fragment:
            target_route += "#" + parts.fragment
        return f'href="{html.escape(target_route, quote=True)}"'

    return re.sub(r'href="([^"]+)"', replace, rendered)


def render_markdown(
    body: str,
    *,
    article: dict[str, Any] | None = None,
    article_by_path: dict[str, dict[str, Any]] | None = None,
    remove_h1: bool = False,
) -> RenderedMarkdown:
    if remove_h1:
        body = re.sub(r"^#\s+.+?\s*\n+", "", body, count=1)
    prepared = preprocess_markdown(body)
    protected, math = protect_math(prepared)
    renderer = SiteRenderer(math)
    markdown = mistune.create_markdown(
        renderer=renderer,
        plugins=["table", "strikethrough", "task_lists", "url"],
    )
    rendered = markdown(protected)
    for token, (replacement, _) in math.items():
        rendered = rendered.replace(token, replacement)
    rendered = sanitize_html(rendered)
    for token, block in renderer.code_replacements.items():
        rendered = rendered.replace(token, block)
    if article is not None and article_by_path is not None:
        rendered = rewrite_article_links(
            rendered, article=article, article_by_path=article_by_path
        )
    return RenderedMarkdown(html=rendered, toc=renderer.toc)


def local_asset_sources(rendered: str) -> list[str]:
    values: list[str] = []
    for raw in re.findall(r'(?:src)="([^"]+)"', rendered):
        parts = urlsplit(html.unescape(raw))
        if not parts.scheme and not parts.netloc and parts.path:
            values.append(unquote(parts.path))
    return values


def validate_local_asset_path(article_path: str, asset: str) -> tuple[Path, Path]:
    source_dir = Path(article_path).parent
    relative = Path(asset)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe local asset path {asset!r} in {article_path}")
    return source_dir / relative, Path(article_path).with_suffix("").parent / relative
