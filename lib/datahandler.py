from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SystemHardwareInfo:
    nvidia: bool
    cpu_vendor: str | None
    amd: bool
    is_vm: bool
    has_bat: bool

    @classmethod
    def from_sys_info(cls, sys_info) -> "SystemHardwareInfo":
        vendor = sys_info.cpu_vendor()
        return cls(
            nvidia=sys_info.has_nvidia_graphics(),
            cpu_vendor=vendor.value if hasattr(vendor, "value") else vendor,
            amd=sys_info.has_amd_graphics(),
            is_vm=sys_info.is_vm(),
            has_bat=sys_info.has_battery(),
        )


# =============================================================================
# Leaf Models
# =============================================================================
@dataclass
class GitRepo:
    username: str
    repos: dict[str, str]

    @property
    def full_repos(self) -> list[str]:
        repos = []
        for repo in self.repos.keys():
            repos.append(f"{self.username}/{repo}")
        return repos

    def local_paths(self, HOME: Path) -> list[Path]:
        """
        Return Paths relative to 'HOME'.
        """
        dest_paths = []
        for partial_dest_str in self.repos.values():
            dest_paths.append(HOME / partial_dest_str)
        return dest_paths


# =============================================================================
# Configurations
# =============================================================================
@dataclass
class GitReposConfiguration:
    repositories: list[GitRepo]

    @classmethod
    def from_arg(cls, arg: dict[str, Any]) -> GitReposConfiguration | None:
        if not arg or not isinstance(arg, dict):
            return None
        username = arg.get("user_name")
        repos = arg.get("repos")
        if not username or not repos:
            return None
        return cls([GitRepo(username, repos)])


@dataclass
class CopySpec:
    source: str
    target: str
    names: list


@dataclass
class KeyCopyConfig:
    ssh_key: CopySpec | None = None
    gpg_key: CopySpec | None = None
    auth_conf: CopySpec | None = None

    @classmethod
    def from_arg(cls, arg: dict[str, Any]) -> "KeyCopyConfig | None":
        if not arg or not isinstance(arg, dict):
            return None

        def parse(name: str) -> CopySpec | None:
            value = arg.get(name)
            if not isinstance(value, dict):
                return None

            source = value.get("source")
            target = value.get("target")
            names = value.get("names", [])

            if not source or not target or not names:
                return None

            return CopySpec(source, target, names)

        cfg = cls(
            ssh_key=parse("ssh_key"),
            gpg_key=parse("gpg_key"),
            auth_conf=parse("auth_conf"),
        )

        if not any((cfg.ssh_key, cfg.gpg_key, cfg.auth_conf)):
            return None

        return cfg

    def all_specs(self) -> list[CopySpec]:
        return [
            spec
            for spec in (
                self.ssh_key,
                self.gpg_key,
                self.auth_conf,
            )
            if spec is not None
        ]


class CopyConfiguration:
    def __init__(
        self,
        copies: list[CopySpec] | None = None,
        key_copy_config: KeyCopyConfig | None = None,
    ):
        self.copies = copies
        self.key_copy_config = key_copy_config
        self.usb = Path("/mnt/usb")
        self.root = Path("/root")

    @classmethod
    def from_arg(cls, arg: Any = None) -> "CopyConfiguration | None":
        if not arg:
            return None
        copies: list[CopySpec] = []
        key_copy_config: KeyCopyConfig | None = None
        if isinstance(arg, list):
            for element in arg:
                if isinstance(element, dict):
                    copies.append(
                        CopySpec(
                            element["source"],
                            element["target"],
                            element.get("names", []),
                        )
                    )
        elif isinstance(arg, dict):
            key_copy_config = KeyCopyConfig.from_arg(arg)
        if not copies and not key_copy_config:
            return None
        return cls(
            copies=copies,
            key_copy_config=key_copy_config,
        )

    def all_specs(self) -> list[CopySpec]:
        specs: list[CopySpec] = []
        if self.copies:
            specs.extend(self.copies)
        if self.key_copy_config:
            specs.extend(self.key_copy_config.all_specs())
        return specs

    def _resolve(
        self, src_base: Path, dst_base: Path, username: str = ""
    ) -> list[tuple[Path, Path]]:
        result = []
        for spec in self.all_specs():
            dst_base = Path(dst_base)
            if not dst_base.is_absolute():
                if username:
                    dst_base = dst_base / "home" / username
            for name in spec.names:
                src = src_base / spec.source / name
                dest = dst_base / spec.target.lstrip("/") / name
                result.append((src, dest))
        return result

    def usb_to_root(self) -> list[tuple[Path, Path]]:
        return self._resolve(self.usb, self.root)

    def root_to_mnt(self, mnt_point: Path, username: str) -> list[tuple[Path, Path]]:
        return self._resolve(src_base=self.root, dst_base=mnt_point, username=username)


@dataclass(slots=True)
class UserService:
    source: str
    target: str
    serv: list[str]

    @classmethod
    def from_arg(cls, v: dict[str, Any]) -> UserService | None:
        return cls(v["source"], v["target"], v.get("serv", []))

    @staticmethod
    def from_list(arg: list[dict[str, Any]] | None) -> list[UserService] | None:
        if not arg:
            return None
        services: list[UserService] = []
        for v in arg:
            if not v:
                continue
            svc = UserService.from_arg(v)
            if svc is not None:
                services.append(svc)
        return services or None

    def source_paths(self, username: str) -> list[Path]:
        base = Path(self.source)
        if not base.is_absolute():
            base = Path("/home") / username / base
        return [base / s for s in self.serv]

    def target_paths(self, username: str) -> list[Path]:
        base = (
            Path("/home")
            / username
            / f".config/systemd/user/{self.target}.target.wants"
        )
        return [base / s for s in self.serv]


# =============================================================================
# Main Config
# =============================================================================
@dataclass
class NoahConfig:
    terminal: str = "kitty"
    parallel_downloads: int = 10
    firefox_browser: str | None = None
    dotfiles_dir: str | None = None
    secret_dotfiles_dir: str | None = None
    dots_git_user_repo: str | None = None
    encrypted_dir: str | None = None
    reflector_options: list[str] | None = None
    disable_svcs: list[str] | None = None
    sudo_defaults: list[str] | None = None
    mask_svcs: list[str] | None = None
    apps_to_hide: list[str] | None = None
    no_extracts: list[str] | None = None
    yazi_plugins: list[str] | None = None
    dirs_icons: dict[str, str] | None = None
    git_repos_config: GitReposConfiguration | None = None
    dotdirs_to_link: list[str] | None = None
    key_copy_config: CopyConfiguration | None = None
    additional_usb_to_cp: CopyConfiguration | None = None
    user_services_config: UserService | None = None

    @classmethod
    def from_config(cls, args: dict[str, Any]) -> "NoahConfig":
        noah = cls()

        if "terminal" in args:
            noah.terminal = args["terminal"]

        if "parallel_downloads" in args:
            noah.parallel_downloads = args["parallel_downloads"]

        if "firefox_browser" in args:
            noah.firefox_browser = args["firefox_browser"]

        if "dotfiles_dir" in args:
            noah.dotfiles_dir = args["dotfiles_dir"]

        if "secret_dotfiles_dir" in args:
            noah.secret_dotfiles_dir = args["secret_dotfiles_dir"]

        if "dots_git_user_repo" in args:
            noah.dots_git_user_repo = args["dots_git_user_repo"]

        if "encrypted_dir" in args:
            noah.encrypted_dir = args["encrypted_dir"]

        if "disable_svcs" in args:
            noah.disable_svcs = args["disable_svcs"]

        if "mask_svcs" in args:
            noah.disable_svcs = args["mask_svcs"]

        if "sudo_defaults" in args:
            noah.sudo_defaults = args["sudo_defaults"]

        if "reflector_options" in args:
            noah.reflector_options = args["reflector_options"]

        if "apps_to_hide" in args:
            noah.apps_to_hide = args["apps_to_hide"]

        if "no_extracts" in args:
            noah.no_extracts = args["no_extracts"]

        if "yazi_plugins" in args:
            noah.yazi_plugins = args["yazi_plugins"]

        if "dirs_icons" in args:
            noah.dirs_icons = args["dirs_icons"]

        if "dotdirs_to_link" in args:
            noah.dotdirs_to_link = args["dotdirs_to_link"]

        if kc := args.get("key_copy_config"):
            noah.key_copy_config = CopyConfiguration.from_arg(kc)

        if usb := args.get("additional_usb_to_cp"):
            noah.additional_usb_to_cp = CopyConfiguration.from_arg(usb)

        if us := args.get("user_services"):
            noah.user_services_config = UserService.from_arg(us)

        if gr := args.get("git_repo_config"):
            noah.git_repos_config = GitReposConfiguration.from_arg(gr)

        return noah
