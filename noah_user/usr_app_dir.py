from pathlib import Path
import shutil
from noah_conf.conf import HOME
from utils import get_logger, run_cmd

log = get_logger("Noah")


def clone_repos(git_user: str, git_repos: list[tuple[Path, str]]):
    kh = HOME / ".ssh" / "known_hosts"
    kh.parent.mkdir(parents=True, exist_ok=True)
    if not kh.exists():
        kh.touch()
    content = kh.read_text(errors="ignore")
    if "github.com" not in content:
        scan = run_cmd(["ssh-keyscan", "-H", "github.com"], True)
        if scan and scan.stdout:
            kh.write_text(content + scan.stdout)
    for path, name in git_repos:
        if not (path / name / ".git").exists():
            path.mkdir(parents=True, exist_ok=True)
            run_cmd(
                [
                    "git",
                    "clone",
                    f"git@github.com:{git_user}/{name}.git",
                    f"{path}/{name.capitalize()}",
                ],
                True,
            )


def install_icon_theme(
    old="#ffffff", new="#F4F5F6", repo="vinceliuice/WhiteSur-icon-theme.git"
):
    icon_dir = HOME / ".local/share/icons/WhiteSur-dark"
    if not icon_dir.exists() or not any(icon_dir.rglob("*")):
        tmp = "/tmp/whitesur-icons"
        if Path(tmp).exists():
            shutil.rmtree(tmp)
        run_cmd(["git", "clone", "--depth=1", f"https://github.com/{repo}", tmp], True)
        run_cmd(["bash", f"{tmp}/install.sh"], True)
        for svg in [p for p in icon_dir.rglob("*.svg") if "scalable" not in p.parts]:
            text = svg.read_text()
            if old in text:
                svg.write_text(text.replace(old, new))
    else:
        log.info("Icons already installed")


def set_folder_icons(home, custom_icons):
    folder_icon_dir = home / ".local/share/icons/WhiteSur-dark/places/scalable"
    for folder, icon in custom_icons:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder_icon_dir / icon
        if path.exists():
            run_cmd(
                ["gio", "set", str(folder), "metadata::custom-icon", f"file://{path}"],
                True,
            )


def hide_app_icons(applications: list[str]) -> None:
    system_dir = Path("/usr/share/applications")
    user_dir = HOME / ".local" / "share" / "applications"
    user_dir.mkdir(parents=True, exist_ok=True)
    hidden_entry = "[Desktop Entry]\nHidden=true\nNoDisplay=true\n"
    for app in applications:
        system_file = system_dir / app
        if system_file.exists():
            (user_dir / app).write_text(hidden_entry)
            log.info("Hidden: %s", app)
        else:
            log.info("Skipping %s, not found", system_file)
