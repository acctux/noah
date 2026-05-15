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
    names: list[str] = field(default_factory=list)


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


@dataclass(slots=True)
class NoahConfig:
    terminal: str = "kitty"
    firefox_browser: str = ""
    dots_repo: str = ""
    reflector_country: str = ""
    git_user: str = ""
    encrypted_dir: str = "Desktop/Encrypted"
    ssh_key_file: "UsbFileCopy" = field(default_factory=lambda: UsbFileCopy())
    gpg_key_file: "UsbFileCopy" = field(default_factory=lambda: UsbFileCopy())
    master_pass_file: "UsbFileCopy" = field(default_factory=lambda: UsbFileCopy())
    auth_conf: "UsbFileCopy" = field(default_factory=lambda: UsbFileCopy())
    all_files_to_cp: list["UsbFileCopy"] = field(default_factory=list)
    parallel_downloads: int = 10
    dir_contents_to_cp: list["UsbDirCopy"] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    dirs_icons: dict[str, str] = field(default_factory=dict)
    mkinit_hooks: list[str] = field(default_factory=list)
    reflector_options: list[str] = field(default_factory=list)
    disable_svcs: list[str] = field(default_factory=list)
    sudo_defaults: list[str] = field(default_factory=list)
    apps_to_hide: list[str] = field(default_factory=list)
    no_extracts: list[str] = field(default_factory=list)
    yazi_plugins: list[str] = field(default_factory=list)
    git_repos: list["GitRepos"] = field(default_factory=list)
    user_services: "UserServices" = field(default_factory=lambda: UserServices([]))
    dirs_to_link: list[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, data: dict):
        fc = data.get("file_copy_config", {})

        def parse_list(cls_type, data_list: list[dict] | None) -> list:
            return [cls_type(**item) for item in (data_list or [])]

        def parse_usb_file_copy_list(data_list: list[dict] | None) -> list[UsbFileCopy]:
            result = []
            for item in data_list or []:
                t_dirs = parse_list(UsbTargetCopy, item.get("target_dirs"))
                result.append(
                    UsbFileCopy(
                        source_dir=item.get("source_dir", ""), target_dirs=t_dirs
                    )
                )
            return result

        def parse_file(name: str) -> UsbFileCopy:
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
            dir_contents_to_cp=parse_list(UsbDirCopy, data.get("dir_contents_to_cp")),
            user_services=UserServices.parse_arg(data.get("user_services")),
        )


@dataclass(slots=True)
class CopyProcessor:
    config: "NoahConfig"
    usb_mnt: Path = Path("/mnt/usb")
    root_dir: Path = Path("/root")  # actual destination root
    _file_paths_cache: dict[str, list[Path]] = field(init=False, default_factory=dict)
    _dir_paths_cache: dict[str, list[Path]] = field(init=False, default_factory=dict)

    # --------- Compute paths ---------
    def compute_key_paths(self, f: "UsbFileCopy") -> dict[str, list[Path]]:
        usb, root, home_rel = [], [], []
        for t in f.target_dirs:
            dest = Path(t.dest or "")
            for fname in t.names:
                usb.append(self.usb_mnt / f.source_dir / fname)
                root.append(self.root_dir / dest / fname)
                home_rel.append(dest / fname)
        return {"usb": usb, "root": root, "home_rel": home_rel}

    def compute_dir_paths(self, d: "UsbDirCopy") -> dict[str, list[Path]]:
        usb, root, home_rel = [], [], []
        for dirname in d.names:
            usb.append(self.usb_mnt / d.source_dir / dirname)
            target_path = Path(d.target_dir)
            if target_path.name == dirname:
                root.append(self.root_dir / target_path)
            else:
                root.append(self.root_dir / target_path / dirname)
            home_rel.append(target_path / dirname)
        return {"usb": usb, "root": root, "home_rel": home_rel}

    # --------- File paths access ---------
    def all_file_paths(self, location: str = "home_rel") -> list[Path]:
        if location not in self._file_paths_cache:
            paths = []
            for file in self.config.all_files_to_cp:
                paths.extend(self.compute_key_paths(file)[location])
            self._file_paths_cache[location] = paths
        return self._file_paths_cache[location]

    def usb_file_paths(self) -> list[Path]:
        return self.all_file_paths("usb")

    def root_file_paths(self) -> list[Path]:
        return self.all_file_paths("root")

    def home_file_paths(self) -> list[Path]:
        return self.all_file_paths("home_rel")

    # --------- Directory paths access ---------
    def all_dir_paths(self, location: str = "home_rel") -> list[Path]:
        if location not in self._dir_paths_cache:
            paths = []
            for d in self.config.dir_contents_to_cp:
                paths.extend(self.compute_dir_paths(d)[location])
            self._dir_paths_cache[location] = paths
        return self._dir_paths_cache[location]

    def usb_dir_paths(self) -> list[Path]:
        return self.all_dir_paths("usb")

    def root_dir_paths(self) -> list[Path]:
        return self.all_dir_paths("root")

    def home_dir_paths(self) -> list[Path]:
        return self.all_dir_paths("home_rel")
