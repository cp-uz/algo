from pathlib import Path

from cpuz.rendering import render_markdown


def test_code_is_escaped_and_unsafe_html_is_removed() -> None:
    body = """# Test\n\n<script>alert(1)</script>\n<img src=x onerror=alert(2)>\n[bad](javascript:alert(3))\n\n```cpp\nif (a < b && c > d) return x & y;\n```\n"""
    rendered = render_markdown(body).html
    lower = rendered.casefold()
    assert "<script" not in lower
    assert "onerror" not in lower
    assert 'href="javascript:' not in lower
    assert "&lt;" in rendered
    assert "&gt;" in rendered
    assert "&amp;" in rendered
    assert 'class="copy-code"' in rendered


def test_code_design_is_light_gray_not_black() -> None:
    css = (Path(__file__).resolve().parents[1] / "assets" / "style.css").read_text().casefold()
    assert "--surface-code: #eef1f4" in css
    assert ".code-block" in css
    assert "overflow-x: auto" in css
