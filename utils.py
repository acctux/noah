import shutil
from pathlib import Path
import sys
import logging
import subprocess
from dataclasses import dataclass, field


#########################
# LOG
#########################
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[34m",  # blue
        logging.WARNING: "\033[93m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[41m",  # red background
    }
    RESET = "\033[0m"
    UNDERLINE = "\033[4m"
    NAME_COLOR = "\033[93m"  # yellow

    def format(self, record):
        colored_name = f"{self.NAME_COLOR}{record.name}{self.RESET}"
        level_color = self.COLORS.get(record.levelno, "")
        colored_message = f"{level_color}{record.getMessage()}{self.RESET}"
        message = f"{colored_name}: {colored_message}"
        if record.levelno == logging.CRITICAL:
            message = f"{self.UNDERLINE}{message}{self.RESET}"
        return message


def get_logger(log_name: str | None = None, level=logging.INFO):
    logger = logging.getLogger(log_name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


log = get_logger("Noah")


@dataclass(slots=True)
class GitRepos:
    username: str = ""
    repos: list[dict] = field(default_factory=list)


# --- Data classes ---
@dataclass(slots=True)
class UsbTargetCopy:
    dest: str = ""
    names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UsbFileCopy:
    source_dir: str = ""
    target_dirs: list[UsbTargetCopy] = field(default_factory=list)


@dataclass(slots=True)
class UsbDirCopy:
    source_dir: str = ""
    target_dir: str = ""
    dir_names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UsrSrv:
    source: str
    target: str
    services: list[str]


@dataclass(slots=True)
class UserServices:
    services: list[UsrSrv] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, data=None):
        parsed = []
        for entry in data or []:
            source = entry.get("source", "")
            for target in entry.get("targets", []):
                parsed.append(
                    UsrSrv(
                        source=source,
                        target=target.get("target", ""),
                        services=target.get("serv", []),
                    )
                )
        return cls(parsed)


def parse_list(cls, data: list[dict] | None) -> list:
    return [cls(**item) for item in (data or [])]


def parse_usb_file_copy_list(data: list[dict] | None) -> list[UsbFileCopy]:
    result = []
    for item in data or []:
        t_dirs = parse_list(UsbTargetCopy, item.get("target_dirs"))
        result.append(
            UsbFileCopy(source_dir=item.get("source_dir", ""), target_dirs=t_dirs)
        )
    return result


@dataclass(slots=True)
class NoahConfig:
    terminal: str = "kitty"
    firefox_browser: str = ""
    dots_repo: str = ""
    reflector_country: str = ""
    git_user: str = ""
    encrypted_dir: str = "Desktop/Encrypted"
    ssh_key_file: UsbFileCopy = field(default_factory=UsbFileCopy)
    gpg_key_file: UsbFileCopy = field(default_factory=UsbFileCopy)
    master_pass_file: UsbFileCopy = field(default_factory=UsbFileCopy)
    auth_conf: UsbFileCopy = field(default_factory=UsbFileCopy)
    all_files_to_cp: list[UsbFileCopy] = field(default_factory=list)
    parallel_downloads: int = 10
    dir_contents_to_cp: list[UsbDirCopy] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    dirs_icons: dict[str, str] = field(default_factory=dict)
    mkinit_hooks: list[str] = field(default_factory=list)
    reflector_options: list[str] = field(default_factory=list)
    disable_svcs: list[str] = field(default_factory=list)
    sudo_defaults: list[str] = field(default_factory=list)
    apps_to_hide: list[str] = field(default_factory=list)
    no_extracts: list[str] = field(default_factory=list)
    yazi_plugins: list[str] = field(default_factory=list)
    git_repos: list[GitRepos] = field(default_factory=list)
    files_to_cp: list[UsbFileCopy] = field(default_factory=list)
    dir_contents_to_cp: list[UsbDirCopy] = field(default_factory=list)
    user_services: UserServices = field(default_factory=UserServices)
    dirs_to_link: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, data: dict):
        fc = data.get("file_copy_config", {})

        def parse_file(name):
            file_cfg = fc.get(name, {})
            targets = parse_list(UsbTargetCopy, file_cfg.get("target_dirs"))
            return UsbFileCopy(
                source_dir=file_cfg.get("source_dir", ""), target_dirs=targets
            )

        ssh, gpg, master, auth = map(
            parse_file,
            ["ssh_key_file", "gpg_key_file", "master_pass_file", "auth_conf"],
        )
        all_files = [ssh, gpg, master, auth] + parse_usb_file_copy_list(
            data.get("additional_files_to_cp")
        )
        return cls(
            terminal=data.get("terminal", "kitty"),
            firefox_browser=data.get("firefox_browser", ""),
            dots_repo=data.get("dots_repo", ""),
            reflector_country=data.get("reflector_country", ""),
            git_user=data.get("git_user", ""),
            encrypted_dir=data.get("encrypted_dir", "Desktop/Encrypted"),
            ssh_key_file=ssh,
            gpg_key_file=gpg,
            master_pass_file=master,
            auth_conf=auth,
            all_files_to_cp=all_files,
            parallel_downloads=data.get("parallel_downloads", 10),
            groups=data.get("groups", []),
            dirs_icons=data.get("dirs_icons", {}),
            mkinit_hooks=data.get("mkinit_hooks", []),
            reflector_options=data.get("reflector_options", []),
            disable_svcs=data.get("disable_svcs", []),
            sudo_defaults=data.get("sudo_defaults", []),
            apps_to_hide=data.get("apps_to_hide", []),
            no_extracts=data.get("no_extracts", []),
            yazi_plugins=data.get("yazi_plugins", []),
            dirs_to_link=data.get("dirs_to_link", []),
            git_repos=parse_list(GitRepos, data.get("git_repos")),
            files_to_cp=parse_list(
                UsbFileCopy, data.get("copy_config", {}).get("files_to_cp")
            ),
            dir_contents_to_cp=parse_list(
                UsbDirCopy, data.get("copy_config", {}).get("dir_contents_to_cp")
            ),
            user_services=UserServices(
                [
                    UsrSrv(s["source"], t["target"], t["serv"])
                    for s in data.get("user_services", [])
                    for t in s.get("targets", [])
                ]
            ),
        )


@dataclass(slots=True)
class UserFileProcessor:
    config: NoahConfig
    usb_mnt: Path = Path("/mnt/usb")
    chroot_root: Path = Path("/mnt")
    sources: dict[str, list[Path]] = field(default_factory=dict)
    special_sources: dict[str, dict[str, Path]] = field(default_factory=dict)

    def __post_init__(self):
        self.special_sources = {
            k: {typ: p[0] for typ, p in self._compute_paths(f).items()}
            for k, f in [
                ("ssh", self.config.ssh_key_file),
                ("gpg", self.config.gpg_key_file),
                ("masterpass", self.config.master_pass_file),
                ("auth_conf", self.config.auth_conf),
            ]
        }
        self.sources = self._compute_paths_list(self.config.all_files_to_cp)

    def _compute_paths(self, f: UsbFileCopy) -> dict[str, list[Path]]:
        usb, chroot, home = [], [], []
        for t in f.target_dirs:
            dest = Path(t.dest or "")
            for fname in t.names:
                usb.append(self.usb_mnt / f.source_dir / fname)
                chroot.append(self.chroot_root / dest / fname)
                home.append(dest / fname)
        return {"usb": usb, "chroot": chroot, "home_rel": home}

    def _compute_paths_list(self, files: list[UsbFileCopy]) -> dict[str, list[Path]]:
        result = {"usb": [], "chroot": [], "home_rel": []}
        for f in files or []:
            p = self._compute_paths(f)
            for k in result:
                result[k].extend(p[k])
        return result

    def get_home_paths(self, username: str) -> list[Path]:
        return [Path("/home") / username / p for p in self.sources.get("home_rel", [])]

    def get_special_home_path(self, username: str, key: str) -> Path | None:
        path = self.special_sources.get(key, {}).get("home_rel")
        return Path("/home") / username / path if path else None


@dataclass(slots=True)
class DirFileProcessor:
    dirs_to_copy: list[UsbDirCopy]
    usb_mnt: Path = Path("/mnt/usb")
    chroot_root: Path = Path("/mnt")
    all_paths: dict[str, list[Path]] = field(init=False)

    def __post_init__(self):
        self.all_paths = {"usb": [], "chroot": [], "home_rel": []}
        for d in self.dirs_to_copy:
            for dirname in d.dir_names:
                self.all_paths["usb"].append(self.usb_mnt / d.source_dir / dirname)
                self.all_paths["chroot"].append(
                    self.chroot_root / d.target_dir / dirname
                )
                self.all_paths["home_rel"].append(Path(d.target_dir) / dirname)

    def get_dest_paths(self, username: str) -> list[Path]:
        result = []
        for p in self.all_paths["home_rel"]:
            if p.is_absolute():
                result.append(p)
            else:
                result.append(Path("/home") / username / p)
        return result


def run_dmc(
    cmd: list[str],
    check: bool = False,
    input_text: str = "",
    shell: bool = False,
    cwd=None,
    interactive=False,
):
    if interactive:
        return subprocess.Popen(cmd).wait()
    log = get_logger("Run CMD")
    try:
        log.info(" ".join(cmd))
        result = subprocess.run(
            cmd,
            text=True,
            check=check,
            capture_output=True,
            input=input_text,
            shell=shell,
            cwd=cwd,
        )
        if result.stdout:
            log.info(f"stdout: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        log.error(f"Command failed: {' '.join(cmd)} (exit {e.returncode})")
        if e.stdout:
            log.info(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log.error(f"stderr: {e.stderr.strip()}")
        return e


def yes_no(prompt: str, default: bool = True) -> bool:
    while True:
        r = (
            input(f"\033[92m{prompt} {'(Y/n)' if default else '(y/N)'}: \033[0m")
            .strip()
            .lower()
        )
        if r == "":
            return default
        if r in ("y"):
            return True
        if r in ("n"):
            return False


#########################
# UTILS
#########################
def copy_file(src: Path, dest: Path) -> None:
    if not src.is_file():
        log.error(f"{src} does not exist")
        return
    dest = dest / src.name if dest.is_dir() else dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    log.info(f"Copied file: {src} -> {dest}")


def copy_dir(src: Path, dest: Path) -> None:
    if not src.is_dir():
        log.error(f"{src} does not exist")
        return
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore_dangling_symlinks=True)
    log.info(f"Copied directory: {src} -> {dest}")


def write_etc_file(mnt_point: Path, files_to_write: dict[str, str]) -> None:
    for filepath, content in files_to_write.items():
        full_path = mnt_point / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open("w") as file:
            file.write(content)
            log.info(f"Content: {content}\nWritten to: {full_path}")


def modify_mkinit(mnt_point: Path, hook: str, after: str) -> None:
    mkinit_conf = f"/{mnt_point}/etc/mkinitcpio.conf"
    with open(mkinit_conf, "r") as mkinit:
        content = mkinit.read().splitlines()
    for i, line in enumerate(content):
        if line.startswith("HOOKS="):
            # Extract hooks between parentheses
            hooks = line[line.find("(") + 1 : line.find(")")].split()
            if hook not in hooks:
                hooks.insert(hooks.index(after) + 1, hook)
            content[i] = f"HOOKS=({' '.join(hooks)})"
    with open(mkinit_conf, "w") as mkinit:
        mkinit.write("\n".join(content) + "\n")
