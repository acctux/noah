from pathlib import Path
import shutil
from noah_conf.conf import HOME
from utils import get_logger, run_cmd

log = get_logger("Noah")


def setup_service(
    user_script: str = "user_setup.py", script_dir: str | None = None
) -> None:
    run_script = HOME / user_script
    if script_dir:
        run_script = HOME / script_dir / user_script
    service_name = f"{run_script.stem}.service"
    service_path = HOME / ".config" / "systemd" / "user" / service_name
    service_path.write_text(f"""[Unit]
Description=Open Alacritty running {user_script} on login
After=graphical-session.target

[Service]
Type=oneshot
ExecStart=/usr/bin/alacritty -e python {run_script}
Restart=no

[Install]
WantedBy=graphical-session.target
""")
    run_cmd(["systemctl", "--user", "enable", service_name])


def ensure_github_known_hosts(HOME: Path):
    kh = HOME / ".ssh" / "known_hosts"
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


def clone_repos(git_user: str, git_repos: list[tuple[Path, str]]):
    for path, name in git_repos:
        repo_path = path / name.capitalize()
        if not any(repo_path.iterdir()):
            repo_path.mkdir(parents=True, exist_ok=True)
            cmd = [
                "git",
                "clone",
                f"git@github.com:{git_user}/{name}.git",
                str(repo_path),
            ]
            if run_cmd(cmd, check=True):
                log.info(f"Cloned {name} into {repo_path}")
            else:
                log.error(f"Failed {cmd}")


def install_icon_theme():
    tmp = Path("/tmp/whitesur-icons")
    if tmp.exists():
        shutil.rmtree(tmp)
    icon_git = "https://github.com/vinceliuice/WhiteSur-icon-theme.git"
    run_cmd(["git", "clone", icon_git, str(tmp)], True)
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


def set_folder_icons(custom_folder_icons: list[tuple[Path, str]], HOME: Path = HOME):
    for folder, icon in custom_folder_icons:
        folder.mkdir(parents=True, exist_ok=True)
        icon = HOME / ".local/share/icons/WhiteSur-dark/places/scalable" / icon
        if icon.exists():
            cmd = ["gio", "set", str(folder), "metadata::custom-icon", f"file://{icon}"]
            run_cmd(cmd, True)


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
