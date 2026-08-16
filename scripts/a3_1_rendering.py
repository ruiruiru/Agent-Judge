#!/usr/bin/env python3
"""Small deterministic vector renderer for Stage A3.1 paper figures.

The module deliberately contains no scientific-computing, model, inference,
embedding, resampling, or metric code.  It renders already-frozen display
values through a shared scene graph to PDF and SVG, then rasterizes the PDF at
300 dpi for preview/QA.
"""

from __future__ import annotations

import html
import math
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

from PIL import Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas


PT_PER_INCH = 72.0
PDF_FONT = "Helvetica"
PDF_FONT_BOLD = "Helvetica-Bold"
SVG_FONT_STACK = "Helvetica, Arial, sans-serif"
WHITE = "#ffffff"
BLACK = "#111111"
DARK = "#333333"
MID = "#777777"
LIGHT = "#d9d9d9"
PALE = "#f2f2f2"
ACCENT = "#1f4e79"
EXPLORATORY = "#8a5a00"


class RenderingError(RuntimeError):
    """Raised when a figure cannot be rendered or violates its geometry."""


def _rgb(hex_color: str) -> tuple[float, float, float]:
    value = hex_color.lstrip("#")
    if len(value) != 6:
        raise RenderingError(f"invalid color: {hex_color}")
    return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))


def _font_name(bold: bool) -> str:
    return PDF_FONT_BOLD if bold else PDF_FONT


def text_width(text: str, size: float, bold: bool = False) -> float:
    """Return the PDF-font width of one text line in points."""

    return pdfmetrics.stringWidth(text, _font_name(bold), size)


def wrap_text(text: str, max_width: float, size: float, bold: bool = False) -> list[str]:
    """Wrap ASCII-oriented text to a maximum width using PDF font metrics."""

    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width(candidate, size, bold) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if any(text_width(line, size, bold) > max_width + 0.01 for line in lines):
        raise RenderingError(f"word exceeds wrap width: {text!r}")
    return lines


@dataclass(frozen=True)
class Primitive:
    """One renderer-neutral drawing primitive."""

    kind: str
    values: dict[str, Any]


@dataclass
class VectorFigure:
    """A minimal scene graph that writes matching PDF and SVG figures."""

    width_in: float
    height_in: float
    title: str
    primitives: list[Primitive] = field(default_factory=list)
    text_bounds: list[tuple[float, float, float, float, str]] = field(default_factory=list)

    @property
    def width(self) -> float:
        return self.width_in * PT_PER_INCH

    @property
    def height(self) -> float:
        return self.height_in * PT_PER_INCH

    def rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: str = WHITE,
        stroke: str = BLACK,
        line_width: float = 0.8,
        dash: Sequence[float] | None = None,
        radius: float = 0.0,
    ) -> None:
        self.primitives.append(
            Primitive(
                "rect",
                {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "fill": fill,
                    "stroke": stroke,
                    "line_width": line_width,
                    "dash": tuple(dash or ()),
                    "radius": radius,
                },
            )
        )

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke: str = BLACK,
        line_width: float = 0.8,
        dash: Sequence[float] | None = None,
    ) -> None:
        self.primitives.append(
            Primitive(
                "line",
                {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "stroke": stroke,
                    "line_width": line_width,
                    "dash": tuple(dash or ()),
                },
            )
        )

    def circle(
        self,
        x: float,
        y: float,
        radius: float,
        *,
        fill: str = WHITE,
        stroke: str = BLACK,
        line_width: float = 0.8,
    ) -> None:
        self.primitives.append(
            Primitive(
                "circle",
                {
                    "x": x,
                    "y": y,
                    "radius": radius,
                    "fill": fill,
                    "stroke": stroke,
                    "line_width": line_width,
                },
            )
        )

    def polygon(
        self,
        points: Sequence[tuple[float, float]],
        *,
        fill: str = WHITE,
        stroke: str = BLACK,
        line_width: float = 0.8,
    ) -> None:
        self.primitives.append(
            Primitive(
                "polygon",
                {
                    "points": tuple(points),
                    "fill": fill,
                    "stroke": stroke,
                    "line_width": line_width,
                },
            )
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 8.0,
        bold: bool = False,
        anchor: str = "left",
        color: str = BLACK,
        line_height: float | None = None,
    ) -> None:
        if anchor not in {"left", "middle", "right"}:
            raise RenderingError(f"unsupported anchor: {anchor}")
        lines = value.split("\n")
        leading = line_height or size * 1.22
        top_y = y + (len(lines) - 1) * leading / 2
        for index, line_value in enumerate(lines):
            line_y = top_y - index * leading
            width = text_width(line_value, size, bold)
            if anchor == "left":
                x0 = x
            elif anchor == "middle":
                x0 = x - width / 2
            else:
                x0 = x - width
            self.text_bounds.append(
                (x0, line_y - size * 0.55, x0 + width, line_y + size * 0.55, line_value)
            )
        self.primitives.append(
            Primitive(
                "text",
                {
                    "x": x,
                    "y": y,
                    "value": value,
                    "size": size,
                    "bold": bold,
                    "anchor": anchor,
                    "color": color,
                    "line_height": leading,
                },
            )
        )

    def arrow(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        stroke: str = DARK,
        line_width: float = 1.0,
        dash: Sequence[float] | None = None,
        head: float = 5.0,
    ) -> None:
        self.line(x1, y1, x2, y2, stroke=stroke, line_width=line_width, dash=dash)
        angle = math.atan2(y2 - y1, x2 - x1)
        left = (
            x2 - head * math.cos(angle) + head * 0.55 * math.sin(angle),
            y2 - head * math.sin(angle) - head * 0.55 * math.cos(angle),
        )
        right = (
            x2 - head * math.cos(angle) - head * 0.55 * math.sin(angle),
            y2 - head * math.sin(angle) + head * 0.55 * math.cos(angle),
        )
        self.polygon((left, (x2, y2), right), fill=stroke, stroke=stroke, line_width=0.3)

    def hatched_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill: str = WHITE,
        stroke: str = BLACK,
        spacing: float = 7.0,
    ) -> None:
        self.rect(x, y, width, height, fill=fill, stroke=stroke)
        line_x = x + spacing
        while line_x < x + width:
            self.line(line_x, y + 1, line_x, y + height - 1, stroke=LIGHT, line_width=0.5)
            line_x += spacing

    def validate_geometry(self, margin: float = 1.0) -> None:
        """Reject text whose approximate bounds leave the figure canvas."""

        problems = []
        for x0, y0, x1, y1, label in self.text_bounds:
            if x0 < -margin or y0 < -margin or x1 > self.width + margin or y1 > self.height + margin:
                problems.append((label, x0, y0, x1, y1))
        if problems:
            raise RenderingError(f"clipped text bounds in {self.title}: {problems[:3]}")

    def save_pdf(self, path: Path) -> None:
        """Write a one-page vector PDF using standard, non-embedded fonts."""

        self.validate_geometry()
        path.parent.mkdir(parents=True, exist_ok=True)
        pdf = canvas.Canvas(str(path), pagesize=(self.width, self.height), pageCompression=1)
        pdf.setTitle(self.title)
        pdf.setAuthor("D9-R1 Stage A3.1")
        pdf.setSubject("Frozen paper figure; no scientific recomputation")
        pdf.setFillColorRGB(*_rgb(WHITE))
        pdf.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        for primitive in self.primitives:
            values = primitive.values
            if primitive.kind == "rect":
                pdf.setFillColorRGB(*_rgb(values["fill"]))
                pdf.setStrokeColorRGB(*_rgb(values["stroke"]))
                pdf.setLineWidth(values["line_width"])
                pdf.setDash(values["dash"])
                if values["radius"]:
                    pdf.roundRect(
                        values["x"], values["y"], values["width"], values["height"],
                        values["radius"], fill=1, stroke=1,
                    )
                else:
                    pdf.rect(
                        values["x"], values["y"], values["width"], values["height"],
                        fill=1, stroke=1,
                    )
            elif primitive.kind == "line":
                pdf.setStrokeColorRGB(*_rgb(values["stroke"]))
                pdf.setLineWidth(values["line_width"])
                pdf.setDash(values["dash"])
                pdf.line(values["x1"], values["y1"], values["x2"], values["y2"])
            elif primitive.kind == "circle":
                pdf.setFillColorRGB(*_rgb(values["fill"]))
                pdf.setStrokeColorRGB(*_rgb(values["stroke"]))
                pdf.setLineWidth(values["line_width"])
                pdf.setDash()
                pdf.circle(values["x"], values["y"], values["radius"], fill=1, stroke=1)
            elif primitive.kind == "polygon":
                pdf.setFillColorRGB(*_rgb(values["fill"]))
                pdf.setStrokeColorRGB(*_rgb(values["stroke"]))
                pdf.setLineWidth(values["line_width"])
                pdf.setDash()
                path_object = pdf.beginPath()
                first_x, first_y = values["points"][0]
                path_object.moveTo(first_x, first_y)
                for point_x, point_y in values["points"][1:]:
                    path_object.lineTo(point_x, point_y)
                path_object.close()
                pdf.drawPath(path_object, fill=1, stroke=1)
            elif primitive.kind == "text":
                pdf.setFillColorRGB(*_rgb(values["color"]))
                pdf.setFont(_font_name(values["bold"]), values["size"])
                lines = values["value"].split("\n")
                leading = values["line_height"]
                top_y = values["y"] + (len(lines) - 1) * leading / 2
                for index, line_value in enumerate(lines):
                    line_y = top_y - index * leading - values["size"] * 0.34
                    width = text_width(line_value, values["size"], values["bold"])
                    x = values["x"]
                    if values["anchor"] == "middle":
                        x -= width / 2
                    elif values["anchor"] == "right":
                        x -= width
                    pdf.drawString(x, line_y, line_value)
            else:
                raise RenderingError(f"unknown primitive: {primitive.kind}")
        pdf.showPage()
        pdf.save()

    def save_svg(self, path: Path) -> None:
        """Write a standalone vector SVG matching the PDF scene graph."""

        self.validate_geometry()
        path.parent.mkdir(parents=True, exist_ok=True)
        output = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.width_in:.3f}in" '
                f'height="{self.height_in:.3f}in" viewBox="0 0 {self.width:.3f} {self.height:.3f}" '
                f'role="img" aria-labelledby="title desc">'
            ),
            f'<title id="title">{html.escape(self.title)}</title>',
            '<desc id="desc">Frozen Stage A3.1 paper figure rendered from traceable source artifacts.</desc>',
            f'<rect x="0" y="0" width="{self.width:.3f}" height="{self.height:.3f}" fill="{WHITE}"/>',
        ]
        for primitive in self.primitives:
            values = primitive.values
            if primitive.kind == "rect":
                y = self.height - values["y"] - values["height"]
                dash = "" if not values["dash"] else f' stroke-dasharray="{",".join(map(str, values["dash"]))}"'
                radius = f' rx="{values["radius"]:.3f}"' if values["radius"] else ""
                output.append(
                    f'<rect x="{values["x"]:.3f}" y="{y:.3f}" width="{values["width"]:.3f}" '
                    f'height="{values["height"]:.3f}" fill="{values["fill"]}" stroke="{values["stroke"]}" '
                    f'stroke-width="{values["line_width"]:.3f}"{dash}{radius}/>'
                )
            elif primitive.kind == "line":
                dash = "" if not values["dash"] else f' stroke-dasharray="{",".join(map(str, values["dash"]))}"'
                output.append(
                    f'<line x1="{values["x1"]:.3f}" y1="{self.height-values["y1"]:.3f}" '
                    f'x2="{values["x2"]:.3f}" y2="{self.height-values["y2"]:.3f}" '
                    f'stroke="{values["stroke"]}" stroke-width="{values["line_width"]:.3f}"{dash}/>'
                )
            elif primitive.kind == "circle":
                output.append(
                    f'<circle cx="{values["x"]:.3f}" cy="{self.height-values["y"]:.3f}" '
                    f'r="{values["radius"]:.3f}" fill="{values["fill"]}" stroke="{values["stroke"]}" '
                    f'stroke-width="{values["line_width"]:.3f}"/>'
                )
            elif primitive.kind == "polygon":
                points = " ".join(
                    f'{x:.3f},{self.height-y:.3f}' for x, y in values["points"]
                )
                output.append(
                    f'<polygon points="{points}" fill="{values["fill"]}" stroke="{values["stroke"]}" '
                    f'stroke-width="{values["line_width"]:.3f}"/>'
                )
            elif primitive.kind == "text":
                anchor = {"left": "start", "middle": "middle", "right": "end"}[values["anchor"]]
                lines = values["value"].split("\n")
                leading = values["line_height"]
                top_y = values["y"] + (len(lines) - 1) * leading / 2
                weight = "700" if values["bold"] else "400"
                for index, line_value in enumerate(lines):
                    line_y = top_y - index * leading
                    output.append(
                        f'<text x="{values["x"]:.3f}" y="{self.height-line_y:.3f}" '
                        f'text-anchor="{anchor}" dominant-baseline="middle" '
                        f'font-family="{SVG_FONT_STACK}" font-size="{values["size"]:.3f}" '
                        f'font-weight="{weight}" fill="{values["color"]}">{html.escape(line_value)}</text>'
                    )
            else:
                raise RenderingError(f"unknown primitive: {primitive.kind}")
        output.append("</svg>")
        path.write_text("\n".join(output) + "\n", encoding="utf-8", newline="\n")


def _poppler_command(arguments: Iterable[str]) -> list[str]:
    executable = shutil.which("pdftoppm")
    if not executable:
        raise RenderingError("pdftoppm is unavailable")
    if executable.lower().endswith((".cmd", ".bat")):
        wrapper = Path(executable).resolve()
        candidates = [
            wrapper.parents[2] / "native" / "poppler" / "Library" / "bin" / "pdftoppm.exe",
            wrapper.parent.parent / "Library" / "bin" / "pdftoppm.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return [str(candidate), *arguments]
        command_shell = os.environ.get("COMSPEC", "cmd.exe")
        quoted = subprocess.list2cmdline([executable, *arguments])
        return [command_shell, "/d", "/c", quoted]
    return [executable, *arguments]


def render_pdf_preview(pdf_path: Path, png_path: Path, dpi: int = 300) -> None:
    """Rasterize a one-page PDF and record exact preview DPI metadata."""

    if dpi < 300:
        raise RenderingError("formal preview DPI must be at least 300")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=png_path.parent) as temporary:
        prefix = Path(temporary) / "preview"
        command = _poppler_command(
            ["-png", "-r", str(dpi), "-singlefile", str(pdf_path), str(prefix)]
        )
        subprocess.run(command, check=True, capture_output=True)
        rendered = prefix.with_suffix(".png")
        if not rendered.exists():
            raise RenderingError(f"pdftoppm did not create {rendered}")
        with Image.open(rendered) as image:
            image.save(png_path, dpi=(dpi, dpi), optimize=True)


def save_figure_bundle(figure: VectorFigure, base_path: Path, dpi: int = 300) -> dict[str, Path]:
    """Save PDF, SVG, and PNG variants for one formal figure."""

    pdf_path = base_path.with_suffix(".pdf")
    svg_path = base_path.with_suffix(".svg")
    png_path = base_path.with_suffix(".png")
    figure.save_pdf(pdf_path)
    figure.save_svg(svg_path)
    render_pdf_preview(pdf_path, png_path, dpi=dpi)
    return {"pdf": pdf_path, "svg": svg_path, "png": png_path}
