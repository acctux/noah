#!/usr/bin/env python3
"""
dotsync — Deploy dotfiles from Polka → ~/
All files/folders are deployed to $HOME with a leading dot.
"""

from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
import fnmatch


# ────────────────────── CONFIG ──────────────────────
DOTDIR_NAME = "Polka"
SKIP = {"*.git*", ".DS_Store", "__pycache__"}
SYMLINK_DIRS = {
    "config/systemd/user",
    "config/nvim",
    "local/bin",
}
# ───────────────────────────────────────────────────

HOME = Path.home()
DOTDIR = HOME / DOTDIR_NAME


def log(msg: str) -> None:
    print("[Polka]", msg)


def safe_rm(path: Path) -> None:
    """Remove file, symlink, or directory safely."""
    if not path.exists():
        return
    if path.is_symlink() or path.is_file():
        log(f"Remove: {path}")
        path.unlink(missing_ok=True)
    elif path.is_dir():
        log(f"Remove tree: {path}")
        shutil.rmtree(path)


def make_link(src: Path, dst: Path) -> None:
    """Create relative symlink src → dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(src, dst.parent)
    if dst.is_symlink() and dst.readlink() == rel:
        log(f"Already linked: {dst} → {rel}")
        return
    safe_rm(dst)
    log(f"Link: {dst} → {rel}")
    dst.symlink_to(rel)


def should_skip(rel: Path) -> bool:
    """Skip if any part of path matches SKIP patterns."""
    return any(fnmatch.fnmatch(part, pat) for part in rel.parts for pat in SKIP)


def is_in_symlink_dir(rel: Path) -> bool:
    """True if rel is inside any SYMLINK_DIRS."""
    return any(rel.is_relative_to(Path(d)) for d in SYMLINK_DIRS)


# ────────────────────── PATH HELPERS ──────────────────────
def dst_from_rel(rel: Path) -> Path:
    """Convert relative path (e.g. bin/myscript) → ~/.bin/myscript"""
    return HOME.joinpath("." + rel.parts[0], *rel.parts[1:])


def dst_from_name(name: str) -> Path:
    """Convert SYMLINK_DIRS entry (e.g. local/bin) → ~/.local/bin"""
    parts = name.split("/")
    return HOME.joinpath("." + parts[0], *parts[1:])


# ───────────────────────────────────────────────────────────


def reload_hypr() -> None:
    try:
        subprocess.run(
            ["hyprctl", "reload"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log("Hyprland reloaded")
    except FileNotFoundError:
        log("hyprctl not found – skipping reload")
    except subprocess.CalledProcessError as e:
        log(f"Hyprland reload failed: {e}")


def polka() -> None:
    if not DOTDIR.is_dir():
        log(f"Error: {DOTDIR} not found or not a directory!")
        return

    # ── 1. Deploy individual files (skip SYMLINK_DIRS) ──
    for src_path in DOTDIR.rglob("*"):
        if not src_path.is_file():
            continue

        rel = src_path.relative_to(DOTDIR)
        if should_skip(rel):
            continue
        if is_in_symlink_dir(rel):
            continue

        dst = dst_from_rel(rel)
        safe_rm(dst)
        make_link(src_path, dst)

    # ── 2. Deploy whole directories as symlinks ──
    for name in SYMLINK_DIRS:
        src = DOTDIR / name
        if not src.exists():
            log(f"Skip missing dir: {src}")
            continue

        dst = dst_from_name(name)
        safe_rm(dst)
        make_link(src, dst)

    reload_hypr()
    log("Deployment complete!")


if __name__ == "__main__":
    polka()
