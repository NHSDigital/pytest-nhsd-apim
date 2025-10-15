#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified SBOM → CSV exporter for SPDX (JSON) and CycloneDX (JSON).

Usage:
  python sbom_json_to_csv.py [input_sbom.json] [output.csv]

Defaults:
  input  = sbom.cdx.json (merged CycloneDX) or sbom.json
  output = sbom.csv

Output columns:
  name, versionInfo, type, supplier, downloadLocation, licenseConcluded,
  licenseDeclared, externalRefs

Also writes a pretty table to 'sbom_table.txt' for convenience.
"""

import json
import csv
import sys
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
from tabulate import tabulate


# ----------------------------- CLI args & defaults ----------------------------

# Prefer CycloneDX name by default, but fall back if not present.
DEFAULT_INPUTS = ["sbom.cdx.json", "sbom.json"]
input_file = None
if len(sys.argv) > 1:
    input_file = sys.argv[1]
else:
    for candidate in DEFAULT_INPUTS:
        if Path(candidate).exists():
            input_file = candidate
            break
if not input_file:
    input_file = "sbom.json"  # last resort

output_file = sys.argv[2] if len(sys.argv) > 2 else "sbom.csv"


# ------------------------------ Format detection ------------------------------

def detect_format(doc: Dict[str, Any]) -> str:
    """
    Return 'spdx' or 'cdx' depending on the SBOM structure.
    """
    if "bomFormat" in doc and str(doc.get("bomFormat")).lower() == "cyclonedx":
        return "cdx"
    if "components" in doc and isinstance(doc["components"], list):
        return "cdx"
    if "packages" in doc and isinstance(doc["packages"], list):
        return "spdx"
    # Heuristics
    if "spdxVersion" in doc:
        return "spdx"
    return "cdx"  # default to CycloneDX if ambiguous


# --------------------------- Field normalization ------------------------------

def first_str(item, default="") -> str:
    return item if isinstance(item, str) else default


def join_nonempty(values: List[str], sep=";") -> str:
    return sep.join([v for v in values if v])


def type_from_purl(purl: str) -> str:
    """
    purl format: type/namespace/name@version?qualifiers#subpath
    We return the 'type' part (e.g., 'pypi', 'npm', 'golang', 'github', etc.)
    """
    if not purl:
        return ""
    # Some SBOMs have full purl like "pkg:pypi/requests@2.32.3"
    # Others embed it in externalRefs referenceLocator (SPDX).
    # Normalize by stripping optional leading 'pkg:' then splitting at '/'.
    p = purl
    if p.startswith("pkg:"):
        p = p[4:]
    # Type is before the first slash
    return p.split("/", 1)[0] if "/" in p else p.split("@")[0].split("?")[0].split("#")[0]


# -------- CycloneDX extractors (components, version, purl, licenses, etc.) ----

def cdx_licenses_str(component: Dict[str, Any]) -> str:
    """
    CycloneDX: component.licenses is a list of license objects:
      { "license": {"id": "MIT"} } or { "license": {"name": "..."} }
    """
    out = []
    for lic in component.get("licenses", []) or []:
        lic_obj = lic.get("license", {})
        out.append(lic_obj.get("id") or lic_obj.get("name") or "")
    return join_nonempty(out)

def cdx_download_location(component: Dict[str, Any]) -> str:
    """
    There is no 'downloadLocation' in CycloneDX. Use externalReferences:
      - prefer type 'distribution', else 'website', else first URL seen.
    """
    refs = component.get("externalReferences", []) or []
    # Newer CycloneDX uses {"type": "...", "url": "..."}
    for pref in ("distribution", "website"):
        for r in refs:
            if r.get("type") == pref and r.get("url"):
                return r["url"]
    for r in refs:
        if r.get("url"):
            return r["url"]
    return ""

def cdx_external_refs(component: Dict[str, Any]) -> str:
    """
    Return a ';'-joined set of reference URLs and the purl when present.
    """
    refs = []
    purl = component.get("purl") or ""
    if purl:
        refs.append(purl)
    for r in component.get("externalReferences", []) or []:
        if r.get("url"):
            refs.append(r["url"])
    return join_nonempty(refs)

def cdx_supplier(component: Dict[str, Any]) -> str:
    """
    CycloneDX supplier is an OrganizationalEntity: {"name": "..."}
    """
    sup = component.get("supplier") or {}
    if isinstance(sup, dict):
        return first_str(sup.get("name"), "")
    return first_str(sup, "")

def normalize_cdx_component(component: Dict[str, Any]) -> Dict[str, str]:
    name = component.get("name", "") or ""
    version = component.get("version", "") or ""
    purl = component.get("purl", "") or ""
    ctype = type_from_purl(purl) or component.get("type", "") or ""

    licenses = cdx_licenses_str(component)
    supplier = cdx_supplier(component)
    download = cdx_download_location(component)
    xrefs = cdx_external_refs(component)

    # Map to SPDX-like columns for CSV continuity
    return {
        "name": name,
        "versionInfo": version,
        "type": ctype,
        "supplier": supplier,
        "downloadLocation": download,
        "licenseConcluded": licenses,  # no direct concluded/declared split in CycloneDX
        "licenseDeclared": licenses,
        "externalRefs": xrefs,
    }


# ------------------------------- SPDX extractors ------------------------------

def spdx_external_refs(pkg: Dict[str, Any]) -> Tuple[str, str]:
    """
    Return (type_from_purl, refs_joined)
    SPDX externalRefs structure:
      {"referenceType":"purl", "referenceLocator":"pkg:pypi/requests@2.32.3"}
    """
    refs = pkg.get("externalRefs", []) or []
    purl_value = ""
    out_refs = []
    for r in refs:
        if r.get("referenceType") == "purl":
            loc = r.get("referenceLocator", "")
            if loc:
                purl_value = purl_value or loc
                out_refs.append(loc)
        elif r.get("referenceLocator"):
            out_refs.append(r["referenceLocator"])
    return type_from_purl(purl_value), join_nonempty(out_refs)

def normalize_spdx_package(pkg: Dict[str, Any]) -> Dict[str, str]:
    name = pkg.get("name", "") or ""
    version = pkg.get("versionInfo", "") or ""
    supplier = pkg.get("supplier", "") or ""
    download = pkg.get("downloadLocation", "") or ""
    lic_concluded = pkg.get("licenseConcluded", "") or ""
    lic_declared = pkg.get("licenseDeclared", "") or ""
    ptype, xrefs = spdx_external_refs(pkg)

    # Try to guess type from SPDXID if purl missing (legacy heuristic)
    if not ptype:
        spdxid = pkg.get("SPDXID", "")
        if isinstance(spdxid, str) and "-" in spdxid:
            parts = spdxid.split("-")
            if len(parts) > 2:
                ptype = parts[2]

    return {
        "name": name,
        "versionInfo": version,
        "type": ptype,
        "supplier": supplier,
        "downloadLocation": download,
        "licenseConcluded": lic_concluded,
        "licenseDeclared": lic_declared,
        "externalRefs": xrefs,
    }


# --------------------------------- Main logic ---------------------------------

def main() -> None:
    with open(input_file, "r", encoding="utf-8") as f:
        sbom = json.load(f)

    fmt = detect_format(sbom)

    if fmt == "cdx":
        items = sbom.get("components", []) or []
        rows = [normalize_cdx_component(c) for c in items]
    else:  # 'spdx'
        items = sbom.get("packages", []) or []
        rows = [normalize_spdx_package(p) for p in items]

    # CSV columns unified across formats
    columns = [
        "name",
        "versionInfo",
        "type",
        "supplier",
        "downloadLocation",
        "licenseConcluded",
        "licenseDeclared",
        "externalRefs",
    ]

    # Write CSV
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=columns)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"[sbom_json_to_csv] Parsed format: {fmt.upper()}, items: {len(rows)}")
    print(f"[sbom_json_to_csv] CSV export complete: {output_file}")

    # Write a pretty table for quick viewing
    table_txt = "sbom_table.txt"
    with open(table_txt, "w", encoding="utf-8") as tf:
        if rows:
            table_data = [[r.get(col, "") for col in columns] for r in rows]
            tf.write(tabulate(table_data, headers=columns, tablefmt="grid"))
        else:
            tf.write("No components found.\n")
    print(f"[sbom_json_to_csv] Wrote table: {table_txt}")


if __name__ == "__main__":
    main()