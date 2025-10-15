import json, csv, sys, os
input_file = sys.argv[1] if len(sys.argv) > 1 else "sbom.cdx.json"
repo_name = sys.argv[2] if len(sys.argv) > 2 else os.getenv("GITHUB_REPOSITORY","unknown-repo").split("/")[-1]
output_file = f"sbom-packages-{repo_name}.csv"

data = json.load(open(input_file, "r", encoding="utf-8"))

# SPDX uses "packages"; CycloneDX uses "components"
items = data.get("packages") or data.get("components") or []

def _name(x): return x.get("name", "")
def _ver(x):  # SPDX: versionInfo ; CycloneDX: version
    return x.get("versionInfo") or x.get("version") or ""
def _type(x):
    # SPDX: try SPDXID or externalRefs; CycloneDX: purl "type" prefix
    if "externalRefs" in x:
        for ref in x["externalRefs"]:
            if ref.get("referenceType") == "purl":
                return ref.get("referenceLocator","").split("/")[0]
    if "purl" in x:
        return x["purl"].split("/")[0]
    return ""

columns = ["name", "type", "version"]
with open(output_file, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=columns); w.writeheader()
    for it in items:
        w.writerow({"name": _name(it), "type": _type(it), "version": _ver(it)})

print(f"Package list CSV generated: {output_file}")