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


# -------------------- Copy Processor --------------------
@dataclass(slots=True)
class CopyProcessor:
    config: "NoahConfig"
    usb_mnt: Path = Path("/mnt/usb")
    chroot_mnt: Path = Path("/mnt")
    root: Path = Path("/root")
    _file_cache: dict[str, list[Path]] = field(init=False, default_factory=dict)
    _dir_cache: dict[str, list[Path]] = field(init=False, default_factory=dict)

    LOCATION_MAP = {"mnt": "mnt", "usb": "usb", "root": "root"}

    # ------------------- PATH HELPERS -------------------

    def _make_path(self, src: Path, dest: Path, name: str, location: str) -> Path:
        if location == "usb":
            return self.usb_mnt / src / name
        base = self.chroot_mnt if location == "mnt" else self.root
        return (
            base / dest.relative_to("/") / name
            if dest.is_absolute()
            else base / dest / name
        )

    def _compute_paths(
        self, items, location: str, source_attr, target_attr, names_attr
    ) -> list[Path]:
        if location not in self.LOCATION_MAP:
            raise ValueError(f"Unknown location: {location}")

        paths = []
        for item in items:
            src = Path(getattr(item, source_attr))
            for t in getattr(item, target_attr, []):
                dest = Path(getattr(t, "dest", t) if hasattr(t, "dest") else t)
                names = getattr(t, names_attr, getattr(item, names_attr, []))
                paths.extend(
                    self._make_path(src, dest, name, location) for name in names
                )
        return paths

    # ------------------- GENERIC PATHS -------------------

    def _get_paths(
        self,
        items_attr: str,
        location: str,
        source_attr: str,
        target_attr: str,
        names_attr: str,
        cache: dict,
    ) -> list[Path]:
        if location not in cache:
            items = getattr(self.config, items_attr)
            cache[location] = self._compute_paths(
                items, location, source_attr, target_attr, names_attr
            )
        return cache[location]

    # ------------------- FILE PATHS -------------------

    def all_file_paths(self, location: str = "mnt") -> list[Path]:
        return self._get_paths(
            "all_files_to_cp",
            location,
            "source_dir",
            "target_dirs",
            "names",
            self._file_cache,
        )

    def mnt_file_paths(self, username: str) -> list[Path]:
        home = Path("/mnt/home") / username
        return [
            home / p.relative_to("/") if p.is_absolute() else p
            for p in self.all_file_paths("mnt")
        ]

    def usb_file_paths(self) -> list[Path]:
        return self.all_file_paths("usb")

    def root_file_paths(self) -> list[Path]:
        return self.all_file_paths("root")

    # ------------------- DIR PATHS -------------------

    def all_dir_paths(self, location: str = "mnt") -> list[Path]:
        return self._get_paths(
            "dir_contents_to_cp",
            location,
            "source_dir",
            "target_dir",
            "dir_names",
            self._dir_cache,
        )

    def mnt_dir_paths(self, username: str) -> list[Path]:
        home = Path("/mnt/home") / username
        return [home / p for p in self.all_dir_paths("mnt")]

    def usb_dir_paths(self) -> list[Path]:
        return self.all_dir_paths("usb")

    def root_dir_paths(self) -> list[Path]:
        return self.all_dir_paths("root")

    # ------------------- HOME KEYS -------------------

    def home_paths_split_by_keys(self, username: str) -> tuple[list[Path], list[Path]]:
        home = Path("/mnt/home") / username
        key_sources = [
            self.config.ssh_key_file,
            self.config.gpg_key_file,
            self.config.master_pass_file,
        ]
        key_files = [
            home / t.dest / name
            for kf in key_sources
            for t in getattr(kf, "target_dirs", [])
            for name in getattr(t, "names", [])
        ]
        other_files = [f for f in self.mnt_file_paths(username) if f not in key_files]
        return key_files, other_files
