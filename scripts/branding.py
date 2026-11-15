#!/usr/bin/env -S uv run --script
# Copyright (c) 2026 Munich Quantum Software Company GmbH
# All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# Licensed under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.

# /// script
# requires-python = ">=3.14"
# dependencies = ["fonttools==4.68.0"]
# ///

"""Generate compact vector lockups while embedding the MQSC SVG byte for byte."""

from __future__ import annotations

import base64
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def lettering(text: str, size: int, x: int, y: int, color: str, tracking: int = 0) -> str:
    """Return outlined lettering without a host-font dependency."""
    with TTFont(ROOT / "brand/Poppins-SemiBold.ttf") as font:
        glyphs = font.getGlyphSet()
        cmap = font.getBestCmap()
        assert cmap is not None, "The bundled font must provide a Unicode character map."
        scale = size / font["head"].__dict__["unitsPerEm"]
        paths = []
        advance = 0
        for char in text:
            glyph = glyphs[cmap[ord(char)]]
            pen = SVGPathPen(glyphs)
            glyph.draw(pen)
            paths.append(f'<path transform="translate({advance})" d="{pen.getCommands()}"/>')
            advance += glyph.width + tracking
    return f'<g fill="{color}" transform="translate({x} {y}) scale({scale:.6f} {-scale:.6f})">{"".join(paths)}</g>'


def symbol(foreground: str = "#000000") -> str:
    """Return the shared routes of the F2/F3 architecture as an open O."""
    return f"""<g fill="none" stroke-linecap="round" stroke-linejoin="round">
<path d="M111 24H80a56 56 0 1 0 0 112h31M111 46H80a34 34 0 1 0 0 68h31" stroke="#3070b3" stroke-width="12"/>
<path d="M80 80h38c13 0 13-30 26-30M80 80h64M118 80c13 0 13 30 26 30" stroke="{foreground}" stroke-width="8"/>
<rect x="70" y="70" width="20" height="20" rx="3" fill="{foreground}"/>
<g fill="{foreground}"><circle cx="146" cy="50" r="7"/><circle cx="146" cy="80" r="7"/>
<circle cx="146" cy="110" r="7"/></g>
</g>"""


def main() -> None:
    """Write accessible, self-contained light/dark lockups and a small product icon."""
    destination = ROOT / "docs/_static"
    logo = base64.b64encode((ROOT / "brand/mqsc.svg").read_bytes()).decode()
    for variant, foreground in (("light", "#000000"), ("dark", "#ffffff")):
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 200" role="img" aria-labelledby="title desc">
<title id="title">MQSC Orchestrator</title><desc id="desc">An open O routes
shared classical computation to quantum devices. MQSC Orchestrator: HPC + QUANTUM.</desc>
<g transform="translate(10 20)">{symbol(foreground)}</g>
<image x="200" y="10" width="114" height="56" href="data:image/svg+xml;base64,{logo}"/>
{lettering("Orchestrator", 72, 196, 137, foreground)}
{lettering("HPC + QUANTUM", 17, 201, 175, foreground, 180)}
</svg>"""
        (destination / f"orchestrator-{variant}.svg").write_text(svg + "\n")
    (destination / "orchestrator-icon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 176 176" role="img" aria-label="MQSC Orchestrator">'
        '<rect width="176" height="176" rx="36" fill="#ffffff"/>'
        '<g transform="translate(8 8)">' + symbol() + "</g></svg>\n"
    )


if __name__ == "__main__":
    main()
