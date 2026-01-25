import shutil
import subprocess
import logging
from pathlib import Path

from noah_conf.conf import HOME

log = logging.getLogger(__name__)


############################
# Helpers
############################
def link_path(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    rel = src.relative_to(dst.parent, walk_up=True)
    if dst.is_symlink() and dst.readlink() == rel:
        return False
    if dst.exists():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink(missing_ok=True)
        log.info(f"Removed: {dst}")
    dst.symlink_to(rel, target_is_directory=src.is_dir())
    log.info(f"Linked: {dst} → {rel}")
    return True


def dotted_destination(src: Path, source_dir: Path, target_dir: Path) -> Path:
    """
    Map DOTS_DIR/config/nvim/init.lua → ~/.config/nvim/init.lua
    "." + parts[0]=config->.config"," *parts[1:] tuple
    """
    parts = src.relative_to(source_dir).parts
    return target_dir / Path("." + parts[0], *parts[1:])


def file_candidates(
    target_dir: Path,
    dotfiles_dir: Path,
    dirs_to_link: list[str],
    individual_dirs: list[tuple[Path, Path]],
):
    for src in dotfiles_dir.rglob("*"):
        if src.is_file():
            rel = src.relative_to(dotfiles_dir)
            if rel.as_posix().startswith(".git"):
                continue
            if any(rel.is_relative_to(Path(d)) for d in dirs_to_link):
                continue
            yield src, dotted_destination(src, dotfiles_dir, target_dir)
    for d in dirs_to_link:
        src = dotfiles_dir / d
        if src.is_dir():
            yield src, dotted_destination(src, dotfiles_dir, target_dir)
    for src_dir, dst_dir in individual_dirs:
        if not src_dir.is_dir():
            continue
        for src in src_dir.rglob("*"):
            if src.is_file():
                yield src, dst_dir / src.relative_to(src_dir)


############################
# Main
############################
def deploy_dotfiles(
    dot_dir: Path, dirs_to_link: list[str], ind_dirs: list[tuple[Path, Path]]
):
    if not dot_dir.is_dir():
        log.error(f"Dotfiles directory not found: {dot_dir}")
        return
    linked = 0
    for src, dst in file_candidates(HOME, dot_dir, dirs_to_link, ind_dirs):
        if link_path(src, dst):
            linked += 1
    if shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], check=False)
        log.info("Hyprland reloaded")
    log.info(f"Linked: {linked}")
