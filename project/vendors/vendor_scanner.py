"""Vendor attestation file discovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VendorFileResult:
    vendor: str
    file_name: str | None
    file_path: str | None
    modified_time: str | None
    found: bool


class VendorScanner:
    """Scan vendor directories and capture latest attestation files."""

    def __init__(self, vendor_roots: dict[str, str], allowed_extensions: Iterable[str]) -> None:
        self.vendor_roots = vendor_roots
        self.allowed_extensions = {ext.lower() for ext in allowed_extensions}

    def _newest_file(self, vendor: str, root: Path) -> VendorFileResult:
        if not root.exists():
            LOGGER.warning("Vendor path missing for %s: %s", vendor, root)
            return VendorFileResult(vendor, None, None, None, False)

        files = [
            file_path
            for file_path in root.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in self.allowed_extensions
        ]
        if not files:
            LOGGER.warning("No attestation files found for vendor %s under %s", vendor, root)
            return VendorFileResult(vendor, None, None, None, False)

        newest = max(files, key=lambda path: path.stat().st_mtime)
        modified_iso = datetime.fromtimestamp(newest.stat().st_mtime).isoformat(timespec="seconds")

        return VendorFileResult(
            vendor=vendor,
            file_name=newest.name,
            file_path=str(newest),
            modified_time=modified_iso,
            found=True,
        )

    def scan(self) -> list[VendorFileResult]:
        """Return latest attestation file information per vendor."""
        results: list[VendorFileResult] = []
        for vendor, root in self.vendor_roots.items():
            results.append(self._newest_file(vendor, Path(root)))
        return results
