from pathlib import Path
import shutil
import subprocess
from noah_lib.utils import get_logger

log = get_logger("Noah")


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


def dotted_destination(src: Path, source_root: Path, target_root: Path) -> Path:
    parts = src.relative_to(source_root).parts
    return target_root / Path("." + parts[0], *parts[1:])


def deploy_dotfiles(dotfiles_dir, home_dir, dirs_to_link, individual_dirs):
    linked = skipped = 0
    if not dotfiles_dir.is_dir():
        log.error(f"Dotfiles directory does not exist: {dotfiles_dir}")
        return
    for src in dotfiles_dir.rglob("*"):
        if not src.is_file():
            skipped += 1
            continue
        if src.relative_to(dotfiles_dir).as_posix().startswith(".git") or any(
            src.relative_to(dotfiles_dir).is_relative_to(Path(d)) for d in dirs_to_link
        ):
            skipped += 1
            continue
        dst = dotted_destination(src, dotfiles_dir, home_dir)
        if link_path(src, dst):
            linked += 1
        else:
            skipped += 1
    for d in dirs_to_link:
        src = dotfiles_dir / d
        if not src.is_dir():
            log.error(f"{src} not found.")
            continue
        dst = dotted_destination(src, dotfiles_dir, home_dir)
        if link_path(src, dst):
            linked += 1
        else:
            skipped += 1
    for src_dir, dst_dir in individual_dirs:
        if not src_dir.is_dir():
            log.error(f"Directory does not exist: {src_dir}")
            continue
        for src_file in src_dir.rglob("*"):
            if not src_file.is_file():
                continue
            dst_file = dst_dir / src_file.relative_to(src_dir)
            if link_path(src_file, dst_file):
                linked += 1
            else:
                skipped += 1
    if shutil.which("hyprctl"):
        subprocess.run(["hyprctl", "reload"], check=False)
        log.info("Hyprland reloaded")
    log.info(f"Linked:{linked} | Skipped: {skipped}")
