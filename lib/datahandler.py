from utils import copy_file, copy_dir
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class GitRepos:
    username: str = ""
    repos: list[dict] = field(default_factory=list)


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
    """Parse a list of dicts into a list of dataclass instances."""
    return [cls(**item) for item in (data or [])]


def parse_usb_file_copy_list(data: list[dict] | None) -> list[UsbFileCopy]:
    """Parse a list of dicts into UsbFileCopy instances with nested UsbTargetCopy."""
    result = []
    for item in data or []:
        t_dirs = parse_list(UsbTargetCopy, item.get("target_dirs") or [])
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
    ssh_key_file: UsbFileCopy = field(default_factory=lambda: UsbFileCopy())
    gpg_key_file: UsbFileCopy = field(default_factory=lambda: UsbFileCopy())
    master_pass_file: UsbFileCopy = field(default_factory=lambda: UsbFileCopy())
    auth_conf: UsbFileCopy = field(default_factory=lambda: UsbFileCopy())
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
    user_services: UserServices = field(default_factory=lambda: UserServices([]))
    dirs_to_link: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, data: dict):
        fc = data.get("file_copy_config", {})

        def parse_file(data: dict | None) -> UsbFileCopy:
            if not data:
                return UsbFileCopy()
            target_dirs = parse_list(UsbTargetCopy, data.get("target_dirs") or [])
            return UsbFileCopy(
                source_dir=data.get("source_dir", ""), target_dirs=target_dirs
            )

        ssh = parse_file(fc.get("ssh_key_file"))
        gpg = parse_file(fc.get("gpg_key_file"))
        master = parse_file(fc.get("master_pass_file"))
        auth = parse_file(fc.get("auth_conf"))
        additional_files = parse_usb_file_copy_list(
            fc.get("additional_files_to_cp") or []
        )
        all_files = [ssh, gpg, master, auth] + additional_files
        git_repos = parse_list(GitRepos, data.get("git_repos") or [])
        dir_contents = parse_list(
            UsbDirCopy, data.get("copy_config", {}).get("dir_contents_to_cp") or []
        )
        user_services = UserServices(
            [
                UsrSrv(s["source"], t["target"], t["serv"])
                for s in data.get("user_services", [])
                for t in s.get("targets", [])
            ]
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
            git_repos=git_repos,
            dir_contents_to_cp=dir_contents,
            user_services=user_services,
        )


@dataclass(slots=True)
class CopyProcessor:
    config: "NoahConfig"
    usb_mnt: Path = Path("/mnt/usb")
    chroot_mnt: Path = Path("/mnt")
    root: Path = Path("/root")

    # ----------------- PATH HELPERS -----------------
    def _make_path(self, dest: Path, name: str, base: Path) -> Path:
        """Compute full path for a file/dir."""
        dest_path = Path(getattr(dest, "dest", dest) if hasattr(dest, "dest") else dest)
        return (
            base / dest_path.relative_to("/") / name
            if dest_path.is_absolute()
            else base / dest_path / name
        )

    def _compute_file_paths(self, items, base: Path) -> list[Path]:
        """Compute full file paths from UsbFileCopy list."""
        paths = []
        for item in items:
            for t in item.target_dirs:
                names = t.names or item.names
                for name in names:
                    paths.append(self._make_path(t, name, base))
        return paths

    def _compute_dir_paths(self, items, base: Path) -> list[Path]:
        """Compute full dir paths from UsbDirCopy list."""
        paths = []
        for item in items:
            names = item.dir_names
            for name in names:
                paths.append(self._make_path(item.target_dir, name, base))
        return paths

    # ----------------- FILE / DIR PATHS -----------------
    def usb_file_paths(self) -> list[Path]:
        return self._compute_file_paths(self.config.all_files_to_cp, self.usb_mnt)

    def root_file_paths(self) -> list[Path]:
        return self._compute_file_paths(self.config.all_files_to_cp, self.root)

    def usb_dir_paths(self) -> list[Path]:
        return self._compute_dir_paths(self.config.dir_contents_to_cp, self.usb_mnt)

    def root_dir_paths(self) -> list[Path]:
        return self._compute_dir_paths(self.config.dir_contents_to_cp, self.root)

    # ----------------- COPY LOGIC -----------------
    @staticmethod
    def copy_paths(paths: list[tuple[Path, Path]]):
        for src, dest in paths:
            if src.is_file():
                copy_file(src, dest)
            elif src.is_dir():
                copy_dir(src, dest)

    def get_missing_root(
        self,
    ) -> tuple[list[tuple[Path, Path]], list[tuple[Path, Path]]]:
        """Return USB files and directories missing in /root."""
        missing_files = [
            (u, r)
            for u, r in zip(self.usb_file_paths(), self.root_file_paths())
            if not r.exists()
        ]
        missing_dirs = [
            (u, r)
            for u, r in zip(self.usb_dir_paths(), self.root_dir_paths())
            if not r.exists()
        ]
        return missing_files, missing_dirs

    def copy_usb_to_root(self):
        """Copy missing USB → /root."""
        missing_files, missing_dirs = self.get_missing_root()
        self.copy_paths(missing_files)
        self.copy_paths(missing_dirs)

    def copy_root_to_mnt(self, username: str):
        """Copy /root → /mnt/home/username."""
        home = self.chroot_mnt / "home" / username
        files = [(r, home / r.relative_to("/")) for r in self.root_file_paths()]
        dirs = [(d, home / d.relative_to("/")) for d in self.root_dir_paths()]
        self.copy_paths(files)
        self.copy_paths(dirs)
