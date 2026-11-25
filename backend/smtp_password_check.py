"""Cleans and checks a Google App Password typed or pasted by a person. Used by the staging and local test scripts.

Google shows the password as four groups of four lowercase letters. Copying it can bring along spaces (sometimes
non-breaking ones), zero-width characters, a line break or quotation marks. None of those belong to the password.
The result never contains the password itself, only counts.
"""
import re

# Whitespace of every kind (including the non-breaking space), zero-width characters, and quote marks.
_NOT_PART_OF_IT = re.compile("[\\s ​-‏⁠﻿\"'`‘’“”]")


def clean_google_app_password(raw: str):
    """Returns (cleaned, problem). problem is "" when the cleaned value looks like an App Password."""
    cleaned = _NOT_PART_OF_IT.sub("", raw or "")
    removed = len(raw or "") - len(cleaned)
    letters = sum(1 for c in cleaned if c.isascii() and c.isalpha())
    digits = sum(1 for c in cleaned if c.isdigit())
    other = len(cleaned) - letters - digits
    if len(cleaned) == 16 and letters == 16:
        return cleaned, ""
    parts = [f"{len(cleaned)} characters after removing {removed} space/quote/invisible character(s)"]
    parts.append(f"{letters} letters, {digits} digits, {other} other symbols")
    if len(cleaned) != 16:
        diff = len(cleaned) - 16
        parts.append(f"{abs(diff)} {'too many' if diff > 0 else 'too few'}")
    if digits or other:
        parts.append("an App Password has only letters")
    return cleaned, "; ".join(parts) + ". An App Password is exactly 16 letters (four groups of four)"
