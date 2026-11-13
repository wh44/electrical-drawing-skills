#!/usr/bin/env python3
"""Locate drawing pages by text; do not infer connectivity or contact states."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys


def selected_pages(value: str | None, total: int) -> list[int]:
    if value is None:
        return list(range(total))
    result: set[int] = set()
    for item in value.split(','):
        parts = item.strip().split('-')
        if len(parts) == 1:
            start = end = int(parts[0])
        elif len(parts) == 2:
            start, end = map(int, parts)
        else:
            raise ValueError('Use page numbers/ranges such as 12,18-20.')
        if not 1 <= start <= end <= total:
            raise ValueError(f'Page range {item!r} is outside 1-{total} or reversed.')
        result.update(range(start - 1, end))
    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path)
    parser.add_argument('--out', type=Path, help='New UTF-8 JSONL file; existing files are preserved.')
    parser.add_argument('--pages', help='1-based PDF page numbers, e.g. 12,18-20.')
    parser.add_argument('--find', action='append', default=[], help='Case-insensitive literal substring; repeat for OR matching.')
    args = parser.parse_args()
    try:
        import pymupdf
    except ImportError:
        parser.error('PyMuPDF is required; use an existing Python environment with pymupdf installed.')
    try:
        source = args.pdf.resolve(strict=True)
        if not source.is_file():
            parser.error('The PDF path must be a file.')
        destination = args.out.resolve() if args.out else None
        if destination is not None and (destination == source or destination.exists()):
            parser.error('Output must be a new file, different from the source PDF.')
        # In-memory reads avoid repeated small file operations on WSL-mounted disks.
        # Keep large documents file-backed to bound extra memory use.
        data = source.read_bytes() if source.stat().st_size <= 128 * 1024 * 1024 else None
        if data is not None:
            digest = hashlib.sha256(data).hexdigest()
            document = pymupdf.open(stream=data, filetype='pdf')
        else:
            checksum = hashlib.sha256()
            with source.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    checksum.update(chunk)
            digest = checksum.hexdigest()
            document = pymupdf.open(source)
        with document:
            if document.needs_pass:
                parser.error('Encrypted PDF requires an unlocked reading copy.')
            pages = selected_pages(args.pages, len(document))
            terms = [term.casefold() for term in args.find]
            if destination is not None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                output = destination.open('x', encoding='utf-8', newline='\n')
            else:
                if hasattr(sys.stdout, 'reconfigure'):
                    sys.stdout.reconfigure(encoding='utf-8')
                output = sys.stdout
            matched = 0
            try:
                for index in pages:
                    page = document[index]
                    text = page.get_text()
                    if terms and not any(term in text.casefold() for term in terms):
                        continue
                    record = {
                        'source': str(source), 'sha256': digest,
                        'pdf_page': index + 1, 'pdf_label': page.get_label(),
                        'width_pt': page.rect.width, 'height_pt': page.rect.height,
                        'text': text,
                    }
                    output.write(json.dumps(record, ensure_ascii=False) + '\n')
                    matched += 1
            finally:
                if output is not sys.stdout:
                    output.close()
        print(f'Read {len(pages)} pages; emitted {matched} records. Text matches need visual verification.', file=sys.stderr)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
