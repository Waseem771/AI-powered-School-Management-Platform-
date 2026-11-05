"""Turns stored text into safe ReportLab markup, and prints Urdu with a font that can show it.

Every piece of stored text goes through here. ReportLab treats text as markup, so an unescaped
"<" in a name would crash the PDF. Its built-in fonts have no Urdu letters, and the Urdu font has
no Latin letters, so each run of text is printed in the font that can show it.

Urdu needs the uharfbuzz package to join its letters. Without it, a clear note is printed
instead, because garbled letters on an official document are worse than a visible gap.
"""
import logging
import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, uharfbuzz
from reportlab.lib.fonts import addMapping
from reportlab.pdfgen.textobject import PDFTextObject

logger = logging.getLogger(__name__)

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
URDU_FONT = "NotoNastaliqUrdu"
URDU_FONT_BOLD = "NotoNastaliqUrdu-Bold"
LATIN_FONT = "Helvetica"
LATIN_FONT_BOLD = "Helvetica-Bold"
# Nastaliq climbs and descends far more than Latin text, and needs this much line height.
URDU_MIN_LEADING = 28
URDU_UNAVAILABLE_NOTE = "(Urdu text: see school record)"

_ARABIC_SCRIPT = "؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿"
# One Urdu run, including the spaces and punctuation between its words.
_URDU_RUN = re.compile(rf"[{_ARABIC_SCRIPT}](?:[\s.'\-]*[{_ARABIC_SCRIPT}])*")


_original_set_rise = PDFTextObject.setRise


def _set_rise_safely(self: PDFTextObject, rise: float) -> None:
    """Works around a ReportLab 5.1.0 bug. Nastaliq raises and lowers many letters, and setRise
    reads the last drawing instruction, which crashes if a stretch of text starts with one."""
    if not self._code:
        self._code.append("")
    _original_set_rise(self, rise)


PDFTextObject.setRise = _set_rise_safely


def _register_urdu_fonts() -> None:
    pdfmetrics.registerFont(TTFont(URDU_FONT, str(FONT_DIR / "NotoNastaliqUrdu-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(URDU_FONT_BOLD, str(FONT_DIR / "NotoNastaliqUrdu-Bold.ttf")))
    addMapping(URDU_FONT, 0, 0, URDU_FONT)
    addMapping(URDU_FONT, 1, 0, URDU_FONT_BOLD)


_register_urdu_fonts()
if uharfbuzz is None:
    logger.warning("uharfbuzz could not be loaded, so PDFs will print a note in place of Urdu text.")


def urdu_supported() -> bool:
    return uharfbuzz is not None


def has_urdu(text: str) -> bool:
    return _URDU_RUN.search(text or "") is not None


def printable(text: str) -> str:
    """The text itself, or a note in place of any Urdu that cannot be printed correctly here."""
    return text if urdu_supported() else _URDU_RUN.sub(URDU_UNAVAILABLE_NOTE, text)


def urdu_markup(text: str, latin_font: str = LATIN_FONT) -> str:
    """Markup for a paragraph whose base font is the Urdu one. Everything else is wrapped."""
    parts = []
    position = 0
    for run in _URDU_RUN.finditer(text):
        if run.start() > position:
            parts.append(f'<font name="{latin_font}">{escape(text[position:run.start()])}</font>')
        parts.append(run.group())
        position = run.end()
    if position < len(text):
        parts.append(f'<font name="{latin_font}">{escape(text[position:])}</font>')
    return "".join(parts)


def urdu_style(style: ParagraphStyle, bold: bool = False) -> ParagraphStyle:
    """The same style, set up for Urdu: right font, joined letters, and room for the tall script."""
    return ParagraphStyle(
        f"{style.name}-urdu",
        parent=style,
        fontName=URDU_FONT_BOLD if bold else URDU_FONT,
        leading=max(style.leading, URDU_MIN_LEADING),
        shaping=1,
    )
