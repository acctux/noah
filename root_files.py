from textwrap import dedent

###########################################################
# ARCHINSTALL CONF
###########################################################
network_files: dict[str, str] = {
    "etc/iwd/main.conf": dedent(
        """\
        [Network]
        NameResolvingService=resolvconf
        """
    ),
    "etc/systemd/system/iwd.service.d/override.conf": dedent(
        """\
        [Service]
        RuntimeDirectory=resolvconf
        ReadWritePaths=/etc/resolv.conf
        """
    ),
    "etc/resolvconf.conf": dedent(
        """\
        resolv_conf=/etc/resolv.conf
        name_servers="::1 127.0.0.1"
        """
    ),
    "etc/chrony.conf": dedent(
        """\
        server 0.arch.pool.ntp.org iburst
        server 1.arch.pool.ntp.org iburst
        server 2.arch.pool.ntp.org iburst
        server 3.arch.pool.ntp.org iburst
        driftfile /var/lib/chrony/drift
        rtcsync
        makestep 1.0 3
        leapseclist /usr/share/zoneinfo/leap-seconds.list
        logdir /var/log/chrony
        log measurements statistics tracking
        allow 127.0.0.1
        """
    ),
    "etc/named.conf": dedent(
        """\
        // vim:set ts=4 sw=4 et:
        tls cloudflare {
            remote-hostname "one.one.one.one";
        };
         options {
            pid-file "/run/named/named.pid";
            directory "/var/named";
            max-cache-size 200m;
            listen-on { 127.0.0.1; };
            listen-on-v6 { ::1; };
            allow-recursion {
                127.0.0.1;
                ::1;
            };
            forward only;
            forwarders port 853 tls cloudflare {
                1.1.1.1; 2606:4700:4700::1111;
                1.0.0.1; 2606:4700:4700::1001;
            };
        // if system time is wrong and can't connect
        //    dnssec-validation no;
        };
         zone "localhost" IN {
            type master;
            file "localhost.zone";
        };
         zone "0.0.127.in-addr.arpa" IN {
            type master;
            file "127.0.0.zone";
        };
        """
    ),
}
etc_files_to_write: dict[str, str] = {
    "etc/sysctl.d/99-sysctl.conf": dedent(
        """\
        vm.max_map_count = 2147483642
        # Disable NMI watchdog
        kernel.nmi_watchdog = 0
        # To hide any kernel messages from the console
        kernel.printk = 3 3 3 3
        # Restricting access to kernel pointers in the proc filesystem
        kernel.kptr_restrict = 2
        # May help prevent losing packets
        net.core.netdev_max_backlog = 4096
        """
    ),
    "etc/conf.d/pacman-contrib": 'PACCACHE_ARGS="-k 2"\n',
    "etc/systemd/journald.conf.d/00-journal-size.conf": dedent(
        """\
        [Journal]
        SystemMaxUse=50M
        """
    ),
    "etc/modprobe.d/blacklist.conf": dedent(
        """\
        # Blacklist the Intel TCO Watchdog/Timer module
        blacklist iTCO_wdt
        # Blacklist the AMD SP5100 TCO Watchdog/Timer module (Required for Ryzen cpus)
        blacklist sp5100_tco"
        """
    ),
    "etc/udisks2/mount_options.conf": dedent(
        """\
        [defaults]
        # 'ntfs' signature, the new 'ntfs3' kernel driver
        ntfs:ntfs3_defaults=uid=$UID,gid=$GID
        ntfs:ntfs3_allow=uid=$UID,gid=$GID,umask,dmask,fmask,iocharset,discard,nodiscard,sparse,nosparse,hidden,nohidden,sys_immutable,showmeta,noshowmeta,prealloc,noprealloc,hide_dot_files,nohide_dot_files,windows_names,nocase,case
        """
    ),
    "etc/udev/rules.d/99-thunderbolt.rules": dedent(
        """\
        ACTION=="add", SUBSYSTEM=="thunderbolt", ATTR{authorized}=="0", ATTR{authorized}="1"
        """
    ),
}
