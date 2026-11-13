#!/usr/bin/env python3
"""Read-only PDF inventory; optionally reuse a trusted local project's rules."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys


def select_pages(spec: str | None, total: int) -> list[int]:
    if spec is None:
        return list(range(1, total + 1))
    selected: set[int] = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            raise ValueError("Empty page token")
        ends = token.split("-")
        if len(ends) == 1:
            start = end = int(ends[0])
        elif len(ends) == 2:
            start, end = map(int, ends)
        else:
            raise ValueError(f"Invalid page range: {token}")
        if min(start, end) < 1 or max(start, end) > total:
            raise ValueError(f"Page out of range 1..{total}: {token}")
        selected.update(range(min(start, end), max(start, end) + 1))
    return sorted(selected)


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_rules(root: Path | None):
    if root is None:
        return None
    for relative in ("main.py", "parser/pdf_vector_parser.py", "core/drawing_scope.py"):
        if not (root / relative).is_file():
            raise ValueError(f"Not a supported project root; missing {relative}: {root}")
    sys.path.insert(0, str(root))
    from parser.pdf_vector_parser import parse_metadata
    from parser.page_classifier import classify_page
    from core.drawing_scope import drawing_group

    return parse_metadata, classify_page, drawing_group


def inspect_page(page, number: int, rules, fitz) -> dict:
    words = [
        {"text": str(word[4]), "bbox": dict(zip(("x0", "y0", "x1", "y1"), word[:4]))}
        for word in page.get_text("words", sort=False)
    ]
    drawings = page.get_drawings()
    line_count = sum(item[0] == "l" for drawing in drawings for item in drawing.get("items", []))
    images = page.get_image_info()
    # Text and drawing coordinates are unrotated; use the same frame for images.
    bounds = page.rect * page.derotation_matrix
    area = max(bounds.get_area(), 1.0)
    largest_image = max(
        ((fitz.Rect(item["bbox"]) & bounds).get_area() / area for item in images),
        default=0.0,
    )
    flags = []
    if not words:
        flags.append("no_extractable_words")
    if not line_count:
        flags.append("no_native_line_segments")
    if largest_image >= 0.7:
        flags.append("large_raster_image_check_scan_or_mixed_page")
    if page.rotation:
        flags.append("rotated_page_check_coordinates")
    metadata = {}
    kind = "UNKNOWN"
    group = None
    if rules:
        parse_metadata, classify_page, drawing_group = rules
        metadata = parse_metadata(words, number)
        kind = classify_page({"metadata": metadata, "words": words}).value
        group = drawing_group(metadata.get("drawing_no"))
        if kind == "OTHER":
            flags.append("other_check_cover_legend_or_unsupported_template")
        if kind in {"S", "T", "W"} and not group:
            flags.append("unresolved_scope_no_automatic_cross_validation")
    else:
        flags.append("project_rules_not_loaded")
    return {
        "pdf_page": number,
        "drawing_no": metadata.get("drawing_no"),
        "sheet_no": metadata.get("sheet_no"),
        "drawing_type": kind,
        "scope": group,
        "title": metadata.get("title"),
        "width_pt": round(bounds.width, 2),
        "height_pt": round(bounds.height, 2),
        "rotation": page.rotation,
        "word_count": len(words),
        "vector_path_count": len(drawings),
        "native_line_count": line_count,
        "image_count": len(images),
        "largest_image_area_ratio": round(largest_image, 4),
        "link_count": len(page.get_links()),
        "flags": flags,
        "preview": None,
    }


def run(args) -> dict:
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise ValueError(
            "PyMuPDF is missing. Use the project's Python environment or install requirements.txt there."
        ) from exc
    pdf = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        raise ValueError(f"PDF not found: {pdf}")
    out = args.out.expanduser().resolve()
    if out.exists():
        raise ValueError(f"Output already exists; choose a new directory: {out}")
    root = args.project_root.expanduser().resolve() if args.project_root else None
    rules = project_rules(root)
    digest = file_hash(pdf)
    records = []
    with fitz.open(pdf) as doc:
        if doc.needs_pass:
            raise ValueError("Encrypted PDF needs an accessible, authorized unencrypted copy")
        if not doc.is_pdf or len(doc) == 0:
            raise ValueError("Input must be a non-empty PDF")
        pages = select_pages(args.pages, len(doc))
        previews = set(select_pages(args.preview_pages, len(doc))) if args.preview_pages else set()
        if not previews.issubset(pages):
            raise ValueError("--preview-pages must be a subset of inspected --pages")
        # Reserve the output only after validating input and all requested pages.
        out.mkdir(parents=True, exist_ok=False)
        for index, number in enumerate(pages, 1):
            page = doc[number - 1]
            record = inspect_page(page, number, rules, fitz)
            if number in previews:
                target = out / f"page_{number:04d}.png"
                scale = min(2.0, 1800 / max(page.rect.width, page.rect.height, 1))
                page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False).save(target)
                record["preview"] = str(target)
            records.append(record)
            if index == 1 or index % 25 == 0 or index == len(pages):
                print(f"Inspected {index}/{len(pages)} (PDF page {number})", file=sys.stderr, flush=True)
        total = len(doc)
    # Refuse to label results with the hash of a PDF that changed during inspection.
    if file_hash(pdf) != digest:
        raise ValueError("PDF changed during inspection; discard this output and retry in a new directory")
    result = {
        "schema": 1,
        "purpose": "preflight_inventory_not_verified_topology",
        "pdf": str(pdf),
        "sha256": digest,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "pymupdf_version": fitz.VersionBind,
        "project_root": str(root) if root else None,
        "rules_loaded": rules is not None,
        "total_pages": total,
        "inspected_pages": pages,
        "full_inventory": len(pages) == total,
        "drawing_type_counts": dict(Counter(row["drawing_type"] for row in records)),
        "flag_counts": dict(Counter(flag for row in records for flag in row["flags"])),
        "pages": records,
    }
    (out / "inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "inventory.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows({**row, "flags": ";".join(row["flags"])} for row in records)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", required=True, type=Path, help="New output directory; existing directories are refused")
    parser.add_argument("--project-root", type=Path, help="Trusted PDF_Vetor_Parser source tree; imports its current rules")
    parser.add_argument("--pages", help="1-based pages, e.g. 1-3,12; defaults to all")
    parser.add_argument("--preview-pages", help="Subset of inspected pages to render as original PNGs")
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        print(f"Preflight failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({
        "inventory": str(args.out.resolve() / "inventory.json"),
        "sha256": result["sha256"],
        "inspected": len(result["inspected_pages"]),
        "total_pages": result["total_pages"],
        "full_inventory": result["full_inventory"],
        "drawing_type_counts": result["drawing_type_counts"],
        "flag_counts": result["flag_counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
