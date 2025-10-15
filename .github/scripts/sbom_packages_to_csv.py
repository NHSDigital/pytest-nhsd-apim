#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dual-mode SBOM → package inventory CSV exporter.

Supports:
  - CycloneDX (JSON): components[].{name, version, purl}
  - SPDX (JSON):     packages[].{name, versionInfo, externalRefs[purl]}

Usage:
  python sbom_packages_to_csv.py [input_sbom.json] [repo_name]

Defaults:
  input    = sbom.cdx.json (else sbom.json if not present)
  repo     = $GITHUB_REPOSITORY right-side (e.g., "my-repo")
  output   = sbom-packages-<repo>.csv
"""

import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# ----------------------------- CLI args & defaults ----------------------------

DEFAULT_INPUTS = ["sbom.cdx.json", "sbom.json"]

if len(sys.argv) > 1:
    INPUT_FILE = sys.argv[1]
else:
    INPUT_FILE = next((p for p in DEFAULT_INPUTS if Path(p).exists()), "sbom.json")

if len(sys.argv) > 2:
    REPO_NAME = sys.argv[2]
else:
    REPO_NAME = os.getenv("GITHUB_REPOSITORY", "unknown-repo").split("/")[-1]

OUTPUT_FILE = f"sbom-packages-{REPO_NAME}.csv"


# ------------------------------ Format detection ------------------------------

def detect_format(doc: Dict[str, Any]) -> str:
    """
    Return 'cdx' for CycloneDX or 'spdx' for SPDX (best-effort).
    """
    if str(doc.get("bomFormat", "")).lower() == "cyclonedx":
        return "cdx"
    if "components" in doc and isinstance(doc["components"], list):
        return "cdx"
    if "spdxVersion" in doc or "packages" in doc:
        return "spdx"
    # Default to CycloneDX if ambiguous
    return "cdx"


# ------------------------------- Utils & mappers ------------------------------

def _norm_str(x: Any) -> str:
    return x if isinstance(x, str) else ""

def type_from_purl(purl: str) -> str:
    """
    Extract purl 'type' (e.g., pypi, npm, maven) from a purl string.
    purl form: pkg:<type>/<namespace>/<name>@<version>?...
    """
    if not purl:
        return ""
    s = purl[4:] if purl.startswith("pkg:") else purl
    # everything before first slash is the type
    if "/" in s:
        return s.split("/", 1)[0]
    # if no '/', attempt to strip at '@', '?', '#'
    for sep in ("@", "?", "#"):
        if sep in s:
            return s.split(sep, 1)[0]
    return s

def rows_from_cyclonedx(doc: Dict[str, Any]) -> Iterable[Tuple[str, str, str]]:
    """
    Yield (name, type, version) from CycloneDX components.
    """
    for c in doc.get("components", []) or []:
        name = _norm_str(c.get("name"))
        version = _norm_str(c.get("version"))
        purl = _norm_str(c.get("purl"))
        ctype = type_from_purl(purl) or _norm_str(c.get("type"))
        yield (name, ctype, version)

def rows_from_spdx(doc: Dict[str, Any]) -> Iterable[Tuple[str, str, str]]:
    """
    Yield (name, type, version) from SPDX packages.
    Type is derived from externalRefs purl if present.
    """
    for p in doc.get("packages", []) or []:
        name = _norm_str(p.get("name"))
        version = _norm_str(p.get("versionInfo"))
        ctype = ""
        for ref in p.get("externalRefs", []) or []:
            if ref.get("referenceType") == "purl":
                ctype = type_from_purl(_norm_str(ref.get("referenceLocator"))) or ctype
        # fallback heuristic from SPDXID (legacy)
        if not ctype:
            spdxid = _norm_str(p.get("SPDXID"))
            if "-" in spdxid:
                parts = spdxid.split("-")
                if len(parts) > 2:
                    ctype = parts[2]
        yield (name, ctype, version)


# ------------------------------------ Main ------------------------------------

def main() -> None:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        sbom = json.load(f)

    fmt = detect_format(sbom)

    if fmt == "cdx":
        rows = list(rows_from_cyclonedx(sbom))
    else:
        rows = list(rows_from_spdx(sbom))

    # Write CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["name", "type", "version"])
        for name, ctype, version in rows:
            writer.writerow([name, ctype, version])

    print(f"[sbom_packages_to_csv] Parsed format: {fmt.upper()}, items: {len(rows)}")
    print(f"[sbom_packages_to_csv] Package list CSV generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()