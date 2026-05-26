from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PathResolver:
    usb: Path = Path("/mnt/usb")
    root: Path = Path("/root")
    mnt: Path = Path("/mnt")
    home: Path = Path("/home")

    # ---------- helpers ----------
    def _clean(self, path: str) -> Path:
        return Path(path.lstrip("/"))

    # ---------- root / usb ----------
    def usb_path(self, *parts: str) -> Path:
        return self.usb.joinpath(*parts)

    def root_path(self, *parts: str) -> Path:
        return self.root.joinpath(*map(self._clean, parts))

    # ---------- home-based ----------
    def home_path(self, username: str, *parts: str) -> Path:
        return self.home / username / Path(*parts)

    def mnt_home_path(self, username: str, *parts: str) -> Path:
        return self.mnt / "home" / username / Path(*parts)


# =============================================================================
# Leaf Models
# =============================================================================
@dataclass
class GitRepo:
    username: str
    repos: dict[str, str]  # key = git name, value = local path

    @property
    def full_repos(self) -> list[str]:
        return [f"{self.username}/{name}" for name in self.repos.keys()]

    def local_paths(self, home: Path) -> list[Path]:
        """
        Return Paths resolved relative to 'home'.
        """
        return [home / dest for dest in self.repos.values()]


# =============================================================================
# Configurations
# =============================================================================
@dataclass
class DotfilesConfiguration:
    dotfiles_dir: str | None = None
    secret_dotfiles_dir: str | None = None
    dirs_to_link: list[str] = field(default_factory=list)

    @classmethod
    def from_arg(cls, arg: dict[str, Any] | None) -> "DotfilesConfiguration":
        if not arg:
            return cls()
        return cls(
            dotfiles_dir=arg.get("dotfiles_dir"),
            secret_dotfiles_dir=arg.get("secret_dotfiles_dir"),
            dirs_to_link=arg.get("dirs_to_link", []),
        )


@dataclass
class GitReposConfiguration:
    repositories: list[GitRepo] = field(default_factory=list)

    @classmethod
    def from_arg(cls, arg: dict[str, Any] | None) -> "GitReposConfiguration":
        if not arg:
            return cls()
        username = arg.get("user_name")
        repos = arg.get("repos")
        if username and repos:
            return cls(repositories=[GitRepo(username=username, repos=repos)])
        return cls()


@dataclass
class KeyCopyConfiguration:
    source_dir: str
    target_dir: str
    keys: dict[str, str]
    resolver: PathResolver = field(default_factory=PathResolver)

    def usb_to_root(self) -> list[tuple[Path, Path]]:
        return FlatCopy(
            source_dir=self.source_dir,
            target_dir=self.target_dir,
            names=list(self.keys.values()),
            resolver=self.resolver,
        ).usb_to_root()

    def root_to_mnt(self, username: str) -> list[tuple[Path, Path]]:
        return FlatCopy(
            source_dir=self.source_dir,
            target_dir=self.target_dir,
            names=list(self.keys.values()),
            resolver=self.resolver,
        ).root_to_mnt(username)


@dataclass
class FlatCopy:
    source_dir: str
    target_dir: str
    names: list[str]
    resolver: PathResolver = field(default_factory=PathResolver)

    def usb_to_root(self) -> list[tuple[Path, Path]]:
        src = self.resolver.usb_path(self.source_dir)
        dst = self.resolver.root_path(self.target_dir)
        return [(src / name, dst / name) for name in self.names]

    def root_to_mnt(self, username: str) -> list[tuple[Path, Path]]:
        src = self.resolver.root_path(self.target_dir)
        dst = self.resolver.mnt_home_path(username, self.target_dir)
        return [(src / name, dst / name) for name in self.names]


@dataclass
class CopyConfiguration:
    copies: list[FlatCopy] = field(default_factory=list)

    @classmethod
    def from_arg(cls, arg: list[dict[str, Any]] | None):
        if not arg:
            return cls()

        return cls(
            copies=[
                FlatCopy(
                    source_dir=copy_target["source_dir"],
                    target_dir=copy_target["target_dir"],
                    names=copy_target["names"],
                )
                for copy_target in arg
            ]
        )


@dataclass
class UserService:
    source: str
    target: str
    serv: list[str]

    @classmethod
    def from_arg(cls, v: dict[str, Any]) -> "UserService":
        return cls(
            source=v["source"],
            target=v["target"],
            serv=v.get("serv", []),
        )

    def source_paths(self, username: str) -> list[Path]:
        source = Path(self.source)
        if not source.is_absolute():
            source = Path("/home") / username / source
        return [source / s for s in self.serv]

    def target_paths(self, username: str) -> list[Path]:
        base = (
            Path("/home")
            / username
            / f".config/systemd/user/{self.target}.target.wants"
        )
        return [base / s for s in self.serv]


@dataclass(slots=True)
class UserServicesConfiguration:
    services: list[UserService] = field(default_factory=list)

    @classmethod
    def from_arg(
        cls,
        arg: list[dict[str, Any]] | None,
    ) -> "UserServicesConfiguration":
        if not arg:
            return cls()
        return cls(services=[UserService.from_arg(v) for v in arg])


# =============================================================================
# Main Config
# =============================================================================
@dataclass
class NoahConfig:
    terminal: str = "kitty"
    firefox_browser: str | None = None
    dotfiles_dir: str | None = None
    secret_dotfiles_dir: str | None = None
    git_user: str | None = None
    dots_repo: str | None = None
    reflector_country: str | None = None
    encrypted_dir: str | None = None
    parallel_downloads: int = 10
    disable_svcs: list[str] | None = None
    sudo_defaults: list[str] | None = None
    apps_to_hide: list[str] | None = None
    no_extracts: list[str] | None = None
    yazi_plugins: list[str] | None = None
    dirs_icons: dict[str, str] = field(default_factory=dict)
    git_repos_config: GitReposConfiguration | None = None
    dotfiles_config: DotfilesConfiguration | None = None
    key_copy_config: KeyCopyConfiguration | None = None
    additional_usb_to_cp_config: CopyConfiguration | None = None
    dir_contents_to_cp_config: CopyConfiguration | None = None
    user_services_config: UserServicesConfiguration | None = None

    @classmethod
    def from_config(cls, args: dict[str, Any]) -> "NoahConfig":
        noah = cls()

        if "terminal" in args:
            noah.terminal = args["terminal"]

        if "firefox_browser" in args:
            noah.firefox_browser = args["firefox_browser"]

        if "dotfiles_dir" in args:
            noah.dotfiles_dir = args["dotfiles_dir"]

        if "secret_dotfiles_dir" in args:
            noah.secret_dotfiles_dir = args["secret_dotfiles_dir"]

        if "git_user" in args:
            noah.git_user = args["git_user"]

        if "dots_repo" in args:
            noah.dots_repo = args["dots_repo"]

        if "reflector_country" in args:
            noah.reflector_country = args["reflector_country"]

        if "encrypted_dir" in args:
            noah.encrypted_dir = args["encrypted_dir"]

        if "parallel_downloads" in args:
            noah.parallel_downloads = args["parallel_downloads"]

        if "disable_svcs" in args:
            noah.disable_svcs = args["disable_svcs"]

        if "sudo_defaults" in args:
            noah.sudo_defaults = args["sudo_defaults"]

        if "apps_to_hide" in args:
            noah.apps_to_hide = args["apps_to_hide"]

        if "no_extracts" in args:
            noah.no_extracts = args["no_extracts"]

        if "yazi_plugins" in args:
            noah.yazi_plugins = args["yazi_plugins"]

        if "dirs_icons" in args:
            noah.dirs_icons = args["dirs_icons"]

        if kc := args.get("key_copy_config"):
            noah.key_copy_config = KeyCopyConfiguration(**kc)

        if dc := args.get("dotfiles_config"):
            noah.dotfiles_config = DotfilesConfiguration.from_arg(dc)

        if usb := args.get("additional_usb_to_cp"):
            noah.additional_usb_to_cp_config = CopyConfiguration.from_arg(usb)

        if dirs := args.get("dir_contents_to_cp"):
            noah.dir_contents_to_cp_config = CopyConfiguration.from_arg(dirs)

        if us := args.get("user_services"):
            noah.user_services_config = UserServicesConfiguration.from_arg(us)

        if gr := args.get("git_repo_config"):
            noah.git_repos_config = GitReposConfiguration.from_arg(gr)

        return noah
