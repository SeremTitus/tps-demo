#!/usr/bin/env python3
"""CI packaging script: reads export_presets.cfg, zips exported folders,
produces a single exported_on_{platform}.zip."""

import os
import re
import sys
import zipfile
from pathlib import Path


def snake_case(s: str) -> str:
    raw = re.sub(r"[^a-z0-9]", "_", s.lower())
    return re.sub(r"_+", "_", raw).strip("_")


def parse_presets(cfg_path: Path) -> list[dict]:
    if not cfg_path.exists():
        return []
    content = cfg_path.read_text(encoding="utf-8")
    presets = []
    cur = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("[preset.") or line.startswith("[preset."):
            if "name" in cur:
                presets.append(cur)
            cur = {}
        elif line.startswith("["):
            if "name" in cur:
                presets.append(cur)
                cur = {}
        else:
            m = re.match(r'^name="([^"]*)"', line)
            if m:
                cur["name"] = m.group(1)
            m = re.match(r'^platform="([^"]*)"', line)
            if m:
                cur["platform"] = m.group(1)
            m = re.match(r'^export_path="([^"]*)"', line)
            if m:
                cur["export_path"] = m.group(1)
    if "name" in cur:
        presets.append(cur)
    return presets


def compute_output_dir(preset: dict, cwd: Path) -> Path | None:
    """Replicate compute_export_output_path logic. Returns the directory to zip."""
    preset_snake = snake_case(preset.get("name", ""))
    export_path = preset.get("export_path", "")

    if export_path:
        out_file = cwd / export_path
        if out_file.exists():
            return out_file.parent
        return None

    out_dir = cwd / "export" / preset_snake
    if out_dir.exists() and any(out_dir.iterdir()):
        return out_dir
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: ci_package.py <output_zip>")
        sys.exit(1)

    output_zip = sys.argv[1]
    cwd = Path.cwd()

    presets = parse_presets(cwd / "export_presets.cfg")
    if not presets:
        print("No export presets found.")
        sys.exit(0)

    artifacts_dir = cwd / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    for preset in presets:
        name = preset.get("name", "unknown")
        ps = snake_case(name)
        out_dir = compute_output_dir(preset, cwd)
        if out_dir is None:
            print(f"  {name} -> NOT FOUND")
            continue
        zip_path = artifacts_dir / f"{ps}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(out_dir.iterdir()):
                if f.is_file():
                    zf.write(f, f.name)
        print(f"  {name} -> {out_dir}")

    zips = list(artifacts_dir.glob("*.zip"))
    if not zips:
        print("No exports produced.")
        sys.exit(1)

    out_path = cwd / output_zip
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for z in zips:
            zf.write(z, z.name)
    print(f"Created {output_zip} with {len(zips)} preset(s)")


if __name__ == "__main__":
    main()
