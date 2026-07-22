"""OOP exporter: render architecture SVG → PNG for assets/images."""

from __future__ import annotations

from pathlib import Path


class ArchitectureDiagramPngExporter:
    """Renders the canonical hybrid cortical architecture SVG to PNG."""

    def __init__(
        self,
        *,
        svg_path: Path,
        png_path: Path,
        output_width: int = 1920,
        output_height: int = 1400,
    ) -> None:
        self._svg_path = svg_path
        self._png_path = png_path
        self._output_width = output_width
        self._output_height = output_height

    def export(self) -> Path:
        import cairosvg

        if not self._svg_path.is_file():
            raise FileNotFoundError(f"SVG missing: {self._svg_path}")
        self._png_path.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(
            url=str(self._svg_path),
            write_to=str(self._png_path),
            output_width=self._output_width,
            output_height=self._output_height,
        )
        size = self._png_path.stat().st_size
        if size < 10_000:
            raise RuntimeError(f"PNG trivial or empty: {size} bytes")
        return self._png_path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    exporter = ArchitectureDiagramPngExporter(
        svg_path=root
        / "Documents"
        / "architecture"
        / "hybrid_cortical_column_current_architecture.svg",
        png_path=root
        / "assets"
        / "images"
        / "hybrid_cortical_column_current_architecture.png",
    )
    out = exporter.export()
    print(f"exported {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
