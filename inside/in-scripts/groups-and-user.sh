#######################################
# Create User and Assign Groups
# Description: Creates groups if missing, then creates new user
# Globals: USER_NAME, SWORDPAS
# Arguments: $@ = list of groups to add the user to
#######################################
create_user() {
  for group in "${USER_GROUPS[@]}"; do
    if ! getent group "$group" >/dev/null; then
      info "Creating missing group: ${group}"
      groupadd "$group"
    fi
  done

  info "Creating user ${USER_NAME}."

  useradd -m -s /bin/zsh -G "$(
    IFS=,
    echo "${USER_GROUPS[*]}"
  )" "${USER_NAME}"

  echo "${USER_NAME}:${SWORDPAS}" | chpasswd

  cat >"/etc/sudoers.d/${USER_NAME}" <<EOF
${USER_NAME} ALL=(ALL:ALL) ALL
Defaults timestamp_timeout=-1
Defaults passwd_tries=10
Defaults env_keep += "EDITOR VISUAL SYSTEMD_EDITOR"
EOF

  chmod 440 "/etc/sudoers.d/${USER_NAME}"
  success "User ${USER_NAME} created and added to groups: ${USER_GROUPS[*]}"
}
