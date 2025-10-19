#!/usr/bin/env python3
import logging
from pathlib import Path
from typing import Set, Optional
import shutil
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Constants
PRIMARY_SOURCE_DIR = Path.home() / "Lit/dots"  # Required public dotfiles
SECRET_SOURCE_DIR = Path.home() / "Lit/secretdots"  # Optional secret dotfiles
TARGET_DIR = Path.home()
EXCEPTIONS: Set[str] = {".git"}

# Dynamically build SOURCE_DIRS based on directory existence
SOURCE_DIRS = [PRIMARY_SOURCE_DIR]
if SECRET_SOURCE_DIR.is_dir():
    SOURCE_DIRS.append(SECRET_SOURCE_DIR)
else:
    logger.info(f"Optional directory '{SECRET_SOURCE_DIR}' does not exist; skipping")


def get_target_paths(source_dir: Path, add_dot: bool = True) -> Set[Path]:
    """Generate relative target paths for files in source_dir, excluding specified patterns."""
    paths = set()
    source_dir = source_dir.resolve()

    for file_path in source_dir.rglob("*"):
        if any(exc in file_path.parts for exc in EXCEPTIONS) or not file_path.is_file():
            continue
        rel_path = file_path.relative_to(source_dir)
        if add_dot and not rel_path.parts[0].startswith("."):
            rel_path = Path(f".{rel_path.parts[0]}", *rel_path.parts[1:])
        paths.add(rel_path)
    return paths


def check_overlap(source_dirs: list[Path]) -> None:
    """Check for overlapping target paths across source directories."""
    if len(source_dirs) < 2:
        logger.info("Only one source directory; skipping overlap check")
        return

    all_paths = [get_target_paths(src) for src in source_dirs]
    for i, paths1 in enumerate(all_paths):
        for j, paths2 in enumerate(all_paths[i + 1:], i + 1):
            overlap = paths1.intersection(paths2)
            if overlap:
                raise ValueError(
                    f"Overlapping paths between {source_dirs[i]} and {source_dirs[j]}: "
                    f"{', '.join(str(p) for p in overlap)}"
                )


def remove_target(target_path: Path, dry_run: bool = False) -> None:
    """Remove a file, directory, or symlink at target_path."""
    if not (target_path.exists() or target_path.is_symlink()):
        return
    try:
        if dry_run:
            logger.info(f"[DRY RUN] Would remove: {target_path}")
        else:
            if target_path.is_dir() and not target_path.is_symlink():
                logger.info(f"Removing directory: {target_path}")
                shutil.rmtree(target_path)
            else:
                logger.info(f"Removing file/symlink: {target_path}")
                target_path.unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Failed to remove {target_path}: {e}")


def link_dotfiles(
    source_dir: Path, target_dir: Path, add_dot: bool = True, dry_run: bool = False
) -> None:
    """Create symlinks for files in source_dir to target_dir with optional dot prefix."""
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()

    if not source_dir.is_dir():
        logger.error(f"Source directory '{source_dir}' does not exist")
        return

    logger.info(f"Processing {source_dir} -> {target_dir} (add_dot={add_dot})")

    for file_path in source_dir.rglob("*"):
        if any(exc in file_path.parts for exc in EXCEPTIONS) or not file_path.is_file():
            continue

        try:
            rel_path = file_path.relative_to(source_dir)
            if add_dot and not rel_path.parts[0].startswith("."):
                rel_path = Path(f".{rel_path.parts[0]}", *rel_path.parts[1:])
            target_path = target_dir / rel_path

            # Remove existing target
            remove_target(target_path, dry_run)

            # Log the symlink action
            relative_source = Path(os.path.relpath(file_path, target_path.parent))
            if dry_run:
                logger.info(f"[DRY RUN] Would link: {target_path} -> {relative_source}")
            else:
                # Create parent directories and symlink
                target_path.parent.mkdir(parents=True, exist_ok=True)
                logger.info(f"Linking {target_path} -> {relative_source}")
                target_path.symlink_to(relative_source)
        except Exception as e:
            logger.error(f"Error linking {file_path} -> {target_path}: {e}")


def main(dry_run: bool = False) -> None:
    """Main function to manage dotfile symlinking."""
    logger.info("Starting dotfile management")
    
    if not SOURCE_DIRS:
        logger.error("No valid source directories found; exiting")
        return
    
    if not PRIMARY_SOURCE_DIR.is_dir():
        logger.error(f"Required source directory '{PRIMARY_SOURCE_DIR}' does not exist; exiting")
        return

    check_overlap(SOURCE_DIRS)

    for source_dir in SOURCE_DIRS:
        logger.info(f"Cleaning targets for {source_dir}")
        for rel_path in get_target_paths(source_dir, add_dot=True):
            remove_target(TARGET_DIR / rel_path, dry_run)

        logger.info(f"Symlinking files from {source_dir}")
        link_dotfiles(source_dir, TARGET_DIR, add_dot=True, dry_run=dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage dotfile symlinks")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without changes")
    args = parser.parse_args()

    main(dry_run=args.dry_run)
