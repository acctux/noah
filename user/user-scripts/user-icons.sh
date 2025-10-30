install_icons() {
  local usr_icons
  usr_icons="/usr/share/icons"
  ti_dir="/tmp/whitesur-icons"

  git clone $ICON_GIT "$ti_dir"
  pushd "$ti_dir" >/dev/null
  ./install.sh -t grey -d "$usr_icons"
  popd >/dev/null
  rm -rf "$ti_dir" "${usr_icons}/WhiteSur-grey-light" "${usr_icons}/capitaine-cursors"
  rm -f "${usr_icons}/WhiteSur-grey/apps/scalable/preferences-system.svg"

  local old_color="#dedede"
  local new_color="#d3dae3"
  local -a files
  mapfile -t files < <(
    fd --type f --extension svg --exclude '*/scalable/*' . "$usr_icons/WhiteSur-grey-dark"
  )
  local -a matches=()
  info "Changing icon colors"

  for f in "${files[@]}"; do
    rg --quiet "$old_color" "$f" && matches+=("$f")
  done
  parallel --jobs 4 "sd '$old_color' '$new_color' {}" ::: "${matches[@]}"
}

create_custom_folders() {
  for folder in "${!CUSTOM_FOLDERS[@]}"; do
    mkdir -p "$folder"
    local icon="${CUSTOM_FOLDERS[$folder]}"

    if [[ -d "$folder" ]] && [[ -f "$icon" ]]; then
      gio set "$folder" metadata::custom-icon "file://$icon"
      info "Set icon '$icon' for folder '$folder'"
    else
      info "Skipping '$folder': folder or icon not found"
    fi
  done
}

user_folders_icons() {
  install_icons
  create_custom_folders
}
