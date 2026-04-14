#!/usr/bin/env python3
"""Convert a ChatGPT single-file MHTML export into a Markdown transcript."""

from __future__ import annotations

import argparse
import html
import mimetypes
import re
from datetime import datetime
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag


MAIN_CONTENT_RE = re.compile(r"^conversation-turn-\d+$")


def collapse_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r" +([,.;:!?])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]])", r"\1", text)
    return text


def wrap_code(text: str) -> str:
    backticks = "`" * (max((len(m.group(0)) for m in re.finditer(r"`+", text)), default=0) + 1)
    return f"{backticks}{text}{backticks}"


def sanitize_filename(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    return cleaned or "asset"


def guess_extension(content_type: str, src: str) -> str:
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/svg+xml": ".svg",
        "image/webp": ".webp",
    }
    if content_type in mapping:
        return mapping[content_type]
    guessed = mimetypes.guess_extension(content_type) or Path(src).suffix
    return guessed if guessed and guessed != ".jpe" else ".jpg"


class AssetStore:
    def __init__(self, output_path: Path, parts_by_location: dict[str, object]):
        self.output_path = output_path
        self.parts_by_location = parts_by_location
        self.assets_dir = output_path.parent / f"{output_path.stem}_assets"
        self.saved_paths: dict[str, str] = {}

    def save_from_src(self, src: str, suggested_name: str) -> str:
        if src in self.saved_paths:
            return self.saved_paths[src]

        part = self.parts_by_location.get(src)
        if part is None:
            return src

        payload = part.get_payload(decode=True)
        content_type = part.get_content_type()
        extension = guess_extension(content_type, src)
        filename = sanitize_filename(suggested_name) + extension
        path = self.assets_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

        relative = path.relative_to(self.output_path.parent).as_posix()
        self.saved_paths[src] = relative
        return relative


class MarkdownRenderer:
    def __init__(self, assets: AssetStore):
        self.assets = assets

    def render_assistant_message(self, message: Tag, turn_index: int) -> str:
        markdown_root = message.select_one("div.markdown")
        if markdown_root is None:
            fallback = collapse_whitespace(message.get_text("\n", strip=True))
            return fallback

        blocks = [self.render_block(child, turn_index, 0) for child in markdown_root.children if self.is_meaningful(child)]
        return self.join_blocks(blocks)

    def render_user_message(self, message: Tag, turn_index: int) -> str:
        blocks: list[str] = []
        seen_text: set[int] = set()
        seen_images: set[int] = set()

        for tag in message.find_all(True):
            if tag.name == "div" and "whitespace-pre-wrap" in (tag.get("class") or []):
                if id(tag) in seen_text:
                    continue
                text = tag.get_text("\n", strip=False).strip()
                if text:
                    blocks.append(text)
                seen_text.add(id(tag))
            elif tag.name == "img" and tag.get("src"):
                if id(tag) in seen_images:
                    continue
                alt = (tag.get("alt") or "Image").strip()
                src = tag["src"]
                label = f"turn-{turn_index:02d}-user-image-{len(seen_images) + 1}"
                rel_path = self.assets.save_from_src(src, label)
                blocks.append(f"![{alt}]({rel_path})")
                seen_images.add(id(tag))

        return self.join_blocks(blocks)

    def is_meaningful(self, node: object) -> bool:
        if isinstance(node, NavigableString):
            return bool(str(node).strip())
        return isinstance(node, Tag)

    def join_blocks(self, blocks: Iterable[str]) -> str:
        cleaned = [block.strip("\n") for block in blocks if block and block.strip()]
        text = "\n\n".join(cleaned)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def render_block(self, node: object, turn_index: int, indent: int) -> str:
        if isinstance(node, NavigableString):
            return collapse_whitespace(str(node)).strip()

        assert isinstance(node, Tag)
        classes = set(node.get("class") or [])

        if node.name == "p":
            return self.render_inline_children(node, turn_index).strip()
        if node.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(node.name[1])
            return f"{'#' * level} {self.render_inline_children(node, turn_index).strip()}"
        if node.name == "hr":
            return "---"
        if node.name == "pre":
            return self.render_code_block(node)
        if node.name in {"ul", "ol"}:
            return self.render_list(node, turn_index, indent)
        if node.name == "blockquote":
            content = self.join_blocks(
                self.render_block(child, turn_index, indent)
                for child in node.children
                if self.is_meaningful(child)
            )
            return "\n".join(f"> {line}" if line else ">" for line in content.splitlines())
        if node.name == "table":
            return self.render_table(node, turn_index)
        if node.name == "div":
            table = node.find("table")
            if table is not None:
                return self.render_table(table, turn_index)
            return self.join_blocks(
                self.render_block(child, turn_index, indent)
                for child in node.children
                if self.is_meaningful(child)
            )
        if node.name == "span" and "katex-display" in classes:
            latex = self.extract_latex(node)
            return f"$$\n{latex}\n$$" if latex else ""
        if node.name == "img" and node.get("src"):
            alt = (node.get("alt") or "Image").strip()
            rel_path = self.assets.save_from_src(node["src"], f"turn-{turn_index:02d}-assistant-image")
            return f"![{alt}]({rel_path})"

        return self.render_inline(node, turn_index).strip()

    def render_inline_children(self, node: Tag, turn_index: int) -> str:
        return collapse_whitespace("".join(self.render_inline(child, turn_index) for child in node.children)).strip()

    def render_inline(self, node: object, turn_index: int) -> str:
        if isinstance(node, NavigableString):
            return html.unescape(str(node))

        assert isinstance(node, Tag)
        classes = set(node.get("class") or [])

        if node.name == "br":
            return "\n"
        if node.name == "code" and node.find_parent("pre") is None:
            return wrap_code(self.render_inline_children(node, turn_index))
        if node.name in {"strong", "b"}:
            return f"**{self.render_inline_children(node, turn_index)}**"
        if node.name in {"em", "i"}:
            return f"*{self.render_inline_children(node, turn_index)}*"
        if node.name == "a":
            href = node.get("href", "")
            label = self.render_inline_children(node, turn_index) or href
            return f"[{label}]({href})"
        if node.name == "img" and node.get("src"):
            alt = (node.get("alt") or "Image").strip()
            rel_path = self.assets.save_from_src(node["src"], f"turn-{turn_index:02d}-inline-image")
            return f"![{alt}]({rel_path})"
        if "katex-display" in classes:
            latex = self.extract_latex(node)
            return f"\n\n$$\n{latex}\n$$\n\n" if latex else ""
        if "katex" in classes:
            latex = self.extract_latex(node)
            return f"${latex}$" if latex else ""

        return "".join(self.render_inline(child, turn_index) for child in node.children)

    def extract_latex(self, node: Tag) -> str:
        annotation = node.find("annotation", attrs={"encoding": "application/x-tex"})
        return annotation.get_text(strip=True) if annotation else ""

    def detect_code_language(self, pre: Tag) -> str:
        tokens = list(pre.stripped_strings)
        if len(tokens) >= 2 and tokens[1] == "Run":
            first = tokens[0]
            if first.isalpha() and len(first) <= 20:
                return first.lower()
        return ""

    def render_code_block(self, pre: Tag) -> str:
        language = self.detect_code_language(pre)
        cm_content = pre.select_one("div.cm-content")
        if cm_content is not None:
            code = self.extract_code_text(cm_content).rstrip("\n")
        else:
            code = pre.get_text("\n", strip=False).strip()
        fence = f"```{language}".rstrip()
        return f"{fence}\n{code}\n```"

    def extract_code_text(self, node: Tag) -> str:
        chunks: list[str] = []

        def walk(current: object) -> None:
            if isinstance(current, NavigableString):
                chunks.append(str(current))
                return
            assert isinstance(current, Tag)
            if current.name == "br":
                chunks.append("\n")
                return
            for child in current.children:
                walk(child)

        walk(node)
        text = "".join(chunks)
        return text.replace("\xa0", " ")

    def render_list(self, list_tag: Tag, turn_index: int, indent: int) -> str:
        lines: list[str] = []
        ordered = list_tag.name == "ol"

        for index, item in enumerate(list_tag.find_all("li", recursive=False), start=1):
            prefix = f"{index}. " if ordered else "- "
            base_indent = "  " * indent

            inline_parts: list[str] = []
            nested_blocks: list[str] = []

            for child in item.children:
                if isinstance(child, NavigableString):
                    text = collapse_whitespace(str(child)).strip()
                    if text:
                        inline_parts.append(text)
                    continue

                assert isinstance(child, Tag)
                if child.name in {"ul", "ol"}:
                    nested_blocks.append(self.render_list(child, turn_index, indent + 1))
                elif child.name == "p":
                    text = self.render_inline_children(child, turn_index)
                    if text:
                        inline_parts.append(text)
                else:
                    text = self.render_inline(child, turn_index).strip()
                    if text:
                        inline_parts.append(text)

            first_line = collapse_whitespace(" ".join(part for part in inline_parts if part)).strip()
            lines.append(f"{base_indent}{prefix}{first_line}".rstrip())
            lines.extend(block for block in nested_blocks if block)

        return "\n".join(lines)

    def render_table(self, table: Tag, turn_index: int) -> str:
        rows: list[list[str]] = []
        for tr in table.find_all("tr", recursive=True):
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                continue
            rows.append([self.render_inline_children(cell, turn_index).replace("|", "\\|") for cell in cells])

        if not rows:
            return ""

        header = rows[0]
        body = rows[1:] if len(rows) > 1 else []
        lines = [
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for row in body:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            lines.append("| " + " | ".join(row[: len(header)]) + " |")
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_path", type=Path, help="Path to the ChatGPT .mhtml export")
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        type=Path,
        default=None,
        help="Output Markdown path (defaults to current directory with the same stem)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input_path.resolve()
    output_path = args.output_path
    if output_path is None:
        output_path = Path.cwd() / f"{input_path.stem}.md"
    else:
        output_path = output_path.resolve()

    with input_path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    parts_by_location = {}
    html_part = None
    for part in message.walk():
        location = part.get("Content-Location")
        if location:
            parts_by_location[location] = part
        if (
            part.get_content_type() == "text/html"
            and location
            and html_part is None
            and location.startswith("https://chatgpt.com/c/")
        ):
            html_part = part

    if html_part is None:
        raise SystemExit("Could not locate the main ChatGPT HTML document inside the MHTML file.")

    html_bytes = html_part.get_payload(decode=True)
    html_text = html_bytes.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html_text, "lxml")

    title = soup.title.get_text(strip=True) if soup.title else input_path.stem
    conversation_url = html_part.get("Content-Location", "")
    turn_sections = [
        section
        for section in soup.select('section[data-testid^="conversation-turn-"]')
        if MAIN_CONTENT_RE.match(section.get("data-testid", ""))
    ]

    assets = AssetStore(output_path, parts_by_location)
    renderer = MarkdownRenderer(assets)

    blocks = [
        f"# {title}",
        "",
        f"- Source MHTML: `{input_path}`",
        f"- Conversation URL: {conversation_url}",
        f"- Converted: {datetime.now().astimezone().isoformat(timespec='seconds')}",
    ]

    for turn_number, section in enumerate(turn_sections, start=1):
        role = (section.get("data-turn") or "unknown").strip().title()
        message_root = section.find(attrs={"data-message-author-role": True})
        if message_root is None:
            continue

        if role.lower() == "assistant":
            content = renderer.render_assistant_message(message_root, turn_number)
        else:
            content = renderer.render_user_message(message_root, turn_number)

        if not content:
            continue

        blocks.extend(
            [
                "",
                "---",
                "",
                f"**Turn {turn_number} - {role}**",
                "",
                content,
            ]
        )

    output_path.write_text("\n".join(blocks).strip() + "\n", encoding="utf-8")

    print(f"Wrote Markdown transcript to: {output_path}")
    if assets.saved_paths:
        print(f"Extracted {len(assets.saved_paths)} asset(s) to: {assets.assets_dir}")
    print(f"Captured turns: {len(turn_sections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
