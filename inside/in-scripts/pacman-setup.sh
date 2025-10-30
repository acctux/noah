s_pac_ed() {
  local pac_conf="/etc/pacman.conf"
  sed -i '/^\s*#\s*Color\s*$/s/^#\s*//' $pac_conf
  sed -i '/^\s*Color\s*$/a ILoveCandy' $pac_conf
  sed -i '/^\s*#\s*\[multilib\]/s/^#\s*//' $pac_conf
  sed -i '/^\[multilib\]/,/^$/{ /^\s*#\s*Include\s*=.*/s/^#\s*// }' $pac_conf
  sed -i '/ParallelDownloads/c\ParallelDownloads = 10' $pac_conf
}

chaotic_repo() {
  chaotic_key_id="3056513887B78AEB"
  key_serv="keyserver.ubuntu.com"

  pacman-key --init
  pacman-key --recv-key "$chaotic_key_id" --keyserver $key_serv
  pacman-key --lsign-key "$chaotic_key_id"

  pacman -U --noconfirm --needed \
    https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst
  pacman -U --noconfirm --needed \
    https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst

  sudo tee -a /etc/pacman.conf >/dev/null <<'EOF'

[chaotic-aur]
Include = /etc/pacman.d/chaotic-mirrorlist
EOF
}

pacman_setup() {
  s_pac_ed
  chaotic_repo
}
