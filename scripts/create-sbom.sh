#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

REPO_ROOT="$(git rev-parse --show-toplevel)"

# 1) Base SBOM for repository (CycloneDX JSON)
syft -o cyclonedx-json . > "${REPO_ROOT}/sbom.cdx.json"

# 2) Per-tool SBOMs (optional) - these will be merged later
for tool in "$@"; do
  echo "Creating SBOM for $tool"
  tool_path="$(command -v "$tool" || true)"
  if [[ -z "$tool_path" ]]; then
    echo "Warning: '$tool' not found in PATH. Skipping." >&2
    continue
  fi
  syft -q -o cyclonedx-json "$tool_path" > "${REPO_ROOT}/sbom.${tool}.cdx.json"
done