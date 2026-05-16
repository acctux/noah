from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict


@dataclass(slots=True)
class GitRepos:
    username: str = ""
    repos: List[dict] = field(default_factory=list)


@dataclass(slots=True)
class UsbTargetCopy:
    dest: str = ""
    names: List[str] = field(default_factory=list)


@dataclass(slots=True)
class UsbFileCopy:
    source_dir: str = ""
    target_dirs: List[UsbTargetCopy] = field(default_factory=list)


@dataclass(slots=True)
class UsbDirCopy:
    source_dir: str = ""
    target_dir: str = ""
    dir_names: List[str] = field(default_factory=list)


@dataclass(slots=True)
class UsrSrv:
    source: str
    target: str
    services: List[str]


@dataclass(slots=True)
class UserServices:
    services: List[UsrSrv] = field(default_factory=list)

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


def parse_list(cls, data: List[dict] | None) -> list:
    """Parse a list of dicts into a list of dataclass instances."""
    return [cls(**item) for item in (data or [])]


def parse_usb_file_copy_list(data: List[dict] | None) -> List[UsbFileCopy]:
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
    all_files_to_cp: List[UsbFileCopy] = field(default_factory=list)
    parallel_downloads: int = 10
    dir_contents_to_cp: List[UsbDirCopy] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    dirs_icons: Dict[str, str] = field(default_factory=dict)
    mkinit_hooks: List[str] = field(default_factory=list)
    reflector_options: List[str] = field(default_factory=list)
    disable_svcs: List[str] = field(default_factory=list)
    sudo_defaults: List[str] = field(default_factory=list)
    apps_to_hide: List[str] = field(default_factory=list)
    no_extracts: List[str] = field(default_factory=list)
    yazi_plugins: List[str] = field(default_factory=list)
    git_repos: List[GitRepos] = field(default_factory=list)
    user_services: UserServices = field(default_factory=lambda: UserServices([]))
    dirs_to_link: List[str] = field(default_factory=list)

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
    config: NoahConfig
    usb_mnt: Path = Path("/mnt/usb")
    chroot_mnt: Path = Path("/mnt")
    root: Path = Path("/root")
    _file_cache: dict[str, List[Path]] = field(init=False, default_factory=dict)
    _dir_cache: dict[str, List[Path]] = field(init=False, default_factory=dict)

    def _compute_paths(
        self, items, location: str, source_attr, target_attr, names_attr
    ):
        """
        Compute paths depending on location:
          - 'usb' → always under usb_mnt / source / name
          - 'mnt' → absolute paths → /mnt/...; relative → dest/name
          - 'root' → absolute → /root/...; relative → /root/dest/name
        """
        paths = []
        for item in items:
            src = Path(getattr(item, source_attr))
            for t in getattr(item, target_attr):
                dest = Path(
                    getattr(t, "dest", t) if isinstance(t, UsbTargetCopy) else t
                )
                for name in getattr(t, names_attr, getattr(item, names_attr, [])):
                    if location == "usb":
                        paths.append(self.usb_mnt / src / name)
                    elif location == "mnt":
                        if dest.is_absolute():
                            # Absolute paths → start at /mnt
                            paths.append(self.chroot_mnt / dest.relative_to("/") / name)
                        else:
                            # Relative paths → under dest
                            paths.append(dest / name)
                    elif location == "root":
                        # Keep absolute paths as /root/... for root, relative stays as dest/name
                        if dest.is_absolute():
                            paths.append(self.root / dest.relative_to("/") / name)
                        else:
                            paths.append(self.root / dest / name)
        return paths

    def home_paths_split_by_keys(self, username: str) -> tuple[list[Path], list[Path]]:
        """
        Returns a tuple (key_files, other_files) in /home/username
        without copying, just paths.
        """
        key_sources = [
            self.config.ssh_key_file,
            self.config.gpg_key_file,
            self.config.master_pass_file,
        ]
        key_files = [
            Path("/home") / username / t.dest / name
            for kf in key_sources
            for t in kf.target_dirs
            for name in t.names
        ]
        all_files = self.mnt_file_paths(username)
        other_files = [f for f in all_files if f not in key_files]
        return key_files, other_files

    def all_file_paths(self, location="mnt"):
        if location not in self._file_cache:
            self._file_cache[location] = self._compute_paths(
                self.config.all_files_to_cp,
                location,
                "source_dir",
                "target_dirs",
                "names",
            )
        return self._file_cache[location]

    def mnt_file_paths(self, username: str):
        f_mnt_paths = []
        for path in self.all_file_paths("mnt"):
            if not path.is_absolute():
                f_mnt_paths.append(path)
            else:
                home_base = Path("/home") / username
                f_mnt_paths.append(home_base / path)
        return f_mnt_paths

    def usb_file_paths(self):
        return self.all_file_paths("usb")

    def root_file_paths(self):
        return self.all_file_paths("chroot")

    def all_dir_paths(self, location="mnt"):
        if location not in self._dir_cache:
            self._dir_cache[location] = self._compute_paths(
                self.config.dir_contents_to_cp,
                location,
                "source_dir",
                "target_dir",
                "dir_names",
            )
        return self._dir_cache[location]

    def mnt_dir_paths(self, username: str):
        return [Path("/home") / username / p for p in self.all_dir_paths("mnt")]

    def usb_dir_paths(self):
        return self.all_dir_paths("usb")

    def root_dir_paths(self):
        return self.all_dir_paths("chroot")
