#!/usr/bin/env python3
"""
dotsync — Symlink Polka/bin → ~/.local/bin and dotfiles → ~/
Safely handles linking and overlap checking based on Bash config variables.
"""

import os
import shutil
from pathlib import Path
import fnmatch
import subprocess
from concurrent.futures import ThreadPoolExecutor
import shlex

# === Prefixed print helper ===
def log(*a, **k):
    """Print message with [Polka] prefix for clarity."""
    print("[Polka]", *a, **k)

# === Parse Bash arrays (associative or regular) ===
def parse_bash_array(conf_path: Path, name: str, assoc: bool = False):
    """
    Extract Bash arrays from conf_user.sh:
    - assoc=True → associative array: returns list of (src, dst)
    - assoc=False → simple array: returns list of Path objects
    """
    if assoc:
        cmd = (
            f"source {shlex.quote(str(conf_path))}; "
            f"for k in \"${{!{name}[@]}}\"; do echo \"$k -> ${{{name}[$k]}}\"; done"
        )
        result = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True, check=True
        )
        pairs = []
        for line in result.stdout.strip().splitlines():
            if "->" in line:
                src, dst = [Path(p.strip()) for p in line.split("->", 1)]
                pairs.append((src, dst))
        return pairs
    else:
        cmd = f"source {shlex.quote(str(conf_path))}; printf '%s\\n' \"${{{name}[@]}}\""
        result = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True, check=True
        )
        return [Path(line.strip()) for line in result.stdout.strip().splitlines() if line.strip()]

# === Local config ===
CONF_PATH = Path(__file__).resolve().parent / "user_configuration.sh"
LINKS = parse_bash_array(CONF_PATH, "DIRECT_LINKS", assoc=True)
DOTDIRS = parse_bash_array(CONF_PATH, "DOT_DIRECTORIES")
SKIP = parse_bash_array(CONF_PATH, "SKIP_PATTERNS")

# === Utilities ===
def targets(src: Path, dot: bool, skip_patterns) -> set[Path]:
    """Return all relative file paths in src, skipping patterns and optionally dot-prefixing."""
    res = set()
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(src)
        if any(fnmatch.fnmatch(p, pat) for p in rel.parts for pat in skip_patterns):
            continue
        if dot and not rel.parts[0].startswith("."):
            rel = Path(f".{rel.parts[0]}", *rel.parts[1:])
        res.add(rel)
    return res

def check_overlap(sources, skip_patterns):
    """Detect overlapping dotfile targets to prevent conflicts."""
    cache = {src: {dst / p for p in targets(src, dot, skip_patterns)}
             for src, dst, dot in sources if src.is_dir()}
    for i, (s1, t1) in enumerate(cache.items()):
        for s2, t2 in list(cache.items())[i+1:]:
            overlap = t1 & t2
            if overlap:
                raise ValueError(f"Overlap: {s1} vs {s2}: {', '.join(map(str, overlap))}")

def rm(p: Path):
    """Safely remove file, symlink, or directory."""
    if p.is_symlink() or p.is_file():
        log(f"Remove: {p}")
        p.unlink(missing_ok=True)
    elif p.is_dir():
        log(f"Remove dir: {p}")
        shutil.rmtree(p)

def link(src: Path, dst: Path):
    """Create relative symlink src → dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(src, dst.parent)
    log(f"Link: {dst} → {rel}")
    dst.symlink_to(rel)

def deploy_dir(src: Path, base: Path, dot: bool, skip_patterns):
    """Link all files from src into base with optional dot-prefix, parallelized."""
    def job(f: Path):
        if not f.is_file():
            return
        rel = f.relative_to(src)
        if any(fnmatch.fnmatch(p, pat) for p in rel.parts for pat in skip_patterns):
            return
        if dot and not rel.parts[0].startswith("."):
            rel = Path(f".{rel.parts[0]}", *rel.parts[1:])
        dst = base / rel
        rm(dst)
        link(f, dst)
    with ThreadPoolExecutor() as pool:
        pool.map(job, src.rglob("*"))

def reload_hypr():
    """Reload Hyprland if available."""
    try:
        log("Reload Hyprland...")
        subprocess.run(["hyprctl", "reload"], check=True)
    except FileNotFoundError:
        log("hyprctl not found — skipping.")
    except subprocess.CalledProcessError as e:
        log(f"Reload failed: {e}")

# === Main ===
def main():
    log("Starting Polka...")
    if not DOTDIRS and not any(src.exists() for src, _ in LINKS):
        log("Nothing to deploy.")
        return

    sources = [(src, dst, False) for src, dst in LINKS if src.exists()]
    sources += [(d, Path.home(), True) for d in DOTDIRS]

    dot_sources = [s for s in sources if s[2]]
    if dot_sources:
        try:
            check_overlap(dot_sources, SKIP)
        except ValueError as e:
            log(f"Error: {e}")
            return

    for src_dir, dst_dir in [(s, d) for s, d, a in sources if not a]:
        log(f"Link directory: {src_dir} → {dst_dir}")
        rm(dst_dir)
        link(src_dir, dst_dir)

    for src_dir, dst_base, dot in [(s, d, a) for s, d, a in sources if a]:
        log(f"Deploy dotfiles: {src_dir} → {dst_base}")
        deploy_dir(src_dir, dst_base, dot, SKIP)

    reload_hypr()
    log("Done!")

if __name__ == "__main__":
    main()
