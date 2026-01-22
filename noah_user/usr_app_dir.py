from pathlib import Path
import shutil
from noah_conf.conf import HOME
from utils import get_logger, run_cmd

log = get_logger("Noah")


def ensure_github_known_hosts(kh: Path = HOME / ".ssh" / "known_hosts"):
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_cmd(["ssh-keyscan", "-H", "github.com"], check=True)
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
            log.info("Added github.com to known_hosts")
        else:
            log.warning("Failed to scan github.com for known_hosts")


def clone_repos(git_user: str, repo_path: Path, name: str):
    repo_path.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            "git",
            "clone",
            f"git@github.com:{git_user}/{name}.git",
            str(repo_path),
        ],
        check=True,
    )
    log.info(f"Cloned {name} into {repo_path}")


def install_icon_theme(
    repo: str = "vinceliuice/WhiteSur-icon-theme.git",
):
    tmp = Path("/tmp/whitesur-icons")
    if tmp.exists():
        shutil.rmtree(tmp)
    run_cmd(["git", "clone", "--depth=1", f"https://github.com/{repo}", str(tmp)], True)
    run_cmd(["bash", f"{tmp}/install.sh"], True)


def recolor_icons(
    old: str = "#ffffff",
    new: str = "#F4F5F6",
    icon_dir: Path = HOME / ".local/share/icons/WhiteSur-dark",
):
    for svg in [p for p in icon_dir.rglob("*.svg") if "scalable" not in p.parts]:
        text = svg.read_text()
        if old in text:
            svg.write_text(text.replace(old, new))


def set_folder_icons(
    custom_folder_icons: list[tuple[Path, str]],
    HOME: Path = HOME,
):
    for folder, icon in custom_folder_icons:
        folder.mkdir(parents=True, exist_ok=True)
        icon_path = HOME / ".local/share/icons/WhiteSur-dark/places/scalable" / icon
        if icon_path.exists():
            run_cmd(
                [
                    "gio",
                    "set",
                    str(folder),
                    "metadata::custom-icon",
                    f"file://{icon_path}",
                ],
                True,
            )


def hide_app_icons(applications: list[str]) -> None:
    system_dir = Path("/usr/share/applications")
    user_dir = HOME / ".local" / "share" / "applications"
    user_dir.mkdir(parents=True, exist_ok=True)
    for app in applications:
        system_file = system_dir / app
        user_file = user_dir / app
        if system_file.exists() and not user_file.exists():
            hide_entry = "[Desktop Entry]\nHidden=true\nNoDisplay=true\n"
            user_file.write_text(hide_entry)
            log.info("Hidden: %s", app)
        else:
            log.info("Skipping %s, not found", system_file)
