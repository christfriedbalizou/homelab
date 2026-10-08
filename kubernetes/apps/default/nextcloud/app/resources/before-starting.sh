#!/bin/sh
set -eu

log() {
  printf '[nextcloud-startup] %s\n' "$*" >&2
}

hook_step=initialization
trap 'result=$?; if [ "$result" -ne 0 ]; then log "Failed: $hook_step (exit $result)"; fi' 0

occ() {
  php /var/www/html/occ --no-interaction "$@"
}

run_step() {
  hook_step=$1
  shift
  log "Starting: $hook_step"
  "$@"
  log "Completed: $hook_step"
}

retry() (
  description=$1
  shift
  attempt=1
  until "$@"; do
    if [ "$attempt" -ge 3 ]; then
      log "$description failed after $attempt attempts"
      exit 1
    fi
    log "$description failed (attempt $attempt/3); retrying in 5 seconds"
    sleep 5
    attempt=$((attempt + 1))
  done
)

app_state() (
  apps=$(occ app:list --output=json) || exit 1
  printf '%s\n' "$apps" | php -r '
    $apps = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
    if (!isset($apps["enabled"], $apps["disabled"])) {
        fwrite(STDERR, "Invalid Nextcloud app inventory\n");
        exit(1);
    }
    $id = $argv[1];
    echo array_key_exists($id, $apps["enabled"]) ? "enabled"
        : (array_key_exists($id, $apps["disabled"]) ? "disabled" : "missing");
  ' "$1"
)

ensure_app() (
  state=$(app_state "$1") || exit 1
  case "$state" in
    enabled) log "$1 is already enabled" ;;
    disabled) occ app:enable "$1" ;;
    missing) occ app:install "$1" ;;
    *) log "Unexpected app state for $1"; exit 1 ;;
  esac
)

disable_app() (
  state=$(app_state "$1") || exit 1
  case "$state" in
    enabled) occ app:disable "$1" ;;
    disabled|missing) log "$1 is already disabled or absent" ;;
    *) log "Unexpected app state for $1"; exit 1 ;;
  esac
)

set_app_config() {
  log "Setting $1/$2"
  occ config:app:set "$1" "$2" --value="$3" >/dev/null
}

configure_office() {
  retry "Enable richdocuments" ensure_app richdocuments
  disable_app richdocumentscode
  disable_app richdocumentscode_arm64
  set_app_config richdocuments wopi_url http://collabora.default.svc.cluster.local:9980
  set_app_config richdocuments public_wopi_url https://collabora.${SECRET_DOMAIN}
  set_app_config richdocuments wopi_callback_url http://nextcloud.default.svc.cluster.local:8080
  set_app_config richdocuments wopi_allowlist "${K8S_CLUSTER_CIDR}"
}

cd /var/www/html
run_step "Nextcloud readiness" retry "Nextcloud readiness" occ status --exit-code
run_step "Nextcloud Office" configure_office
