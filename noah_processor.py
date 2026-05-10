from dataclasses import dataclass, field


def parse_list(cls, values):
    return [cls.parse_arg(v) for v in (values or [])]


@dataclass(slots=True)
class GitRepos:
    user: str = ""
    repos: dict = field(default_factory=dict)

    @classmethod
    def parse_arg(cls, data):
        return cls(
            user=data.get("user", ""),
            repos=data.get("repos", {}),
        )


@dataclass(slots=True)
class UsbFileCopy:
    target_dir: str = ""
    files: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CopyGroup:
    source: str = ""
    to_cp_list: list[UsbFileCopy] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, data: dict):
        data = data or {}
        return cls(
            source=data.get("source", ""),
            to_cp_list=[
                UsbFileCopy(target_dir=target_dir, files=files)
                for target_dir, files in data.get("destinations", {}).items()
            ],
        )


@dataclass(slots=True)
class UsrSrv:
    source: str = ""
    target: str = ""
    services: list = field(default_factory=list)


@dataclass(slots=True)
class UserServices:
    services: list[UsrSrv] = field(default_factory=list)

    @classmethod
    def parse_arg(cls, data=None):
        data = data or {}
        return cls(
            services=[
                UsrSrv(source=source, target=target, services=services)
                for source, targets in data.items()
                for target, services in targets.items()
            ]
        )


# =========================================================
# Main config
# =========================================================
@dataclass(slots=True)
class NoahConfig:
    terminal: str
    firefox_browser: str
    dots_repo: str
    git_user: str
    encrypted_dir: str
    ssh_key_file: str
    gpg_key_file: str
    master_pass_file: str
    my_pass: str
    wireguard_dir: str
    parallel_downloads: int
    groups: list[str]
    dirs_icons: dict[str, str]
    mkinit_hooks: list[str]
    reflector_options: list[str]
    custom_services: list[str]
    disable_svcs: list[str]
    apps_to_hide: list[str]
    no_extracts: list[str]
    yazi_plugins: list[str]
    git_repos: list[GitRepos]
    to_cp: list[CopyGroup]
    user_services: UserServices
    dirs_to_link: list[str]

    @classmethod
    def from_config(cls, data):
        data = data or {}
        return cls(
            terminal=data.get("terminal", "kitty"),
            firefox_browser=data.get("firefox_browser", ""),
            dots_repo=data.get("dots_repo", ""),
            git_user=data.get("git_user", ""),
            encrypted_dir=data.get("encrypted_dir", "Desktop/Encrypted"),
            ssh_key_file=data.get("ssh_key_file", "id_ed25519"),
            gpg_key_file=data.get("gpg_key_file", "my_sec_gpg.asc"),
            master_pass_file=data.get("master_pass_file", "pass.txt"),
            my_pass=data.get("my_pass", "users.json"),
            wireguard_dir=data.get("wireguard_dir", "wireguard"),
            parallel_downloads=data.get("parallel_downloads", 10),
            groups=data.get("groups", []),
            mkinit_hooks=data.get("mkinit_hooks", []),
            reflector_options=data.get("reflector_options", []),
            custom_services=data.get("custom_services", []),
            disable_svcs=data.get("disable_svcs", []),
            apps_to_hide=data.get("apps_to_hide", []),
            no_extracts=data.get("no_extracts", []),
            yazi_plugins=data.get("yazi_plugins", []),
            dirs_to_link=data.get("dirs_to_link", []),
            git_repos=parse_list(GitRepos, data.get("git_repos")),
            to_cp=parse_list(CopyGroup, data.get("to_cp")),
            dirs_icons=data.get("dirs_icons", {}),
            user_services=UserServices.parse_arg(data.get("user_services")),
        )
