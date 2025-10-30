clone_gits() {
  mkdir -p "${GIT_DIR}"
  cd "${GIT_DIR}"

  ssh-keyscan github.com >>~/.ssh/known_hosts 2>/dev/null

  for repo in "${GIT_REPOS[@]}"; do
    if [[ -d "$repo" ]]; then
      info "$repo already exists."
      continue
    else
      git clone "git@github.com:${GIT_USER}/$repo.git"
      info "Cloned $repo."
    fi
  done
}

gtk_dotfiles() {
  local theme_dir="$HOME/.themes/Sweet-Ambar-Blue-Dark/gtk-4.0"
  local gtk_config_dir="$HOME/.config/gtk-4.0"
  log INFO "Creating GTK theme symlinks..."
  mkdir -p "$gtk_config_dir"
  ln -sf "$theme_dir/gtk.css" "$gtk_config_dir/gtk.css"
  ln -sf "$theme_dir/gtk-dark.css" "$gtk_config_dir/gtk-dark.css"
}

refresh_caches() {
  fc-cache -f
  if command -v tldr &>/dev/null; then
    tldr --update
  fi
}

# --- Sourcing Hidden Variables ---
decrypt_and_source_secrets() {
  local tmpfile
  tmpfile=$(mktemp) || fatal "Failed to create temporary file."
  ensure_mode "$tmpfile" 600

  if ! gpg --quiet --decrypt "${MY_PASS}" >"$tmpfile"; then
    rm -f "$tmpfile"
    fatal "Failed to decrypt secrets."
  fi

  source "$tmpfile"
  rm -f "$tmpfile"

  if [[ -z "${MY_PASS:-}" ]]; then
    fatal "MY_PASS variable is not set after decryption."
  fi
}

launch_applications() {
  local apps=(
    wl-copy
    brave
    protonmail-bridge
    steam-native-runtime
    dbeaver
    betterbird
  )

  info "Launching main applications..."
  for cmd in "${apps[@]}"; do
    check_dependencies "$cmd"
  done

  echo "${MY_PASS}" | wl-copy ||
    error "Failed to copy password to clipboard."

  brave &>/dev/null &
  protonmail-bridge &>/dev/null &
  steam-native-runtime &>/dev/null &
  betterbird &>/dev/null &

  run_temp_app dbeaver "$DBEAVER_DELAY"
}

init_db() {
  if [[ ! -d /var/lib/mysql/mysql ]]; then
    info "Initializing MariaDB data directory..."
    sudo mariadb-install-db \
      --basedir=/usr \
      --datadir=/var/lib/mysql \
      --auth-root-authentication-method=socket \
      --skip-test-db \
      --user=mysql ||
      error "Database initialization failed."
  else
    info "MariaDB data directory already initialized."
  fi
}

set_db_password() {
  sudo systemctl start mariadb

  if sudo mariadb -e "SELECT 1;" >/dev/null 2>&1; then
    info "Switching root authentication from socket to password..."
    sudo mariadb -e "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('${SWORDPAS}');"
    info "Reloading privileges..."
    sudo mariadb -e "FLUSH PRIVILEGES;"
  else
    info "Root already requires a password or database inaccessible."
  fi
}
