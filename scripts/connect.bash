#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: ./connect.bash [options] [host:port]

Start a Fabric Minecraft client on a Linux server and connect it to a server.
Real rendering through Xvfb is the default. The HeadlessMC -lwjgl stub is
available only as an explicit diagnostic mode and cannot produce real PNGs.

Options:
  --server HOST:PORT          Minecraft server (default: 127.0.0.1:59916)
  --java PATH                 Java executable (Java 21+)
  --launcher PATH             headlessmc-launcher.jar
  --minecraft-version VER     Fabric/Minecraft version (default: 1.21.11)
  --game-dir PATH             Minecraft data and game directory
                              (default: $HOME/.minecraft)
  --probe-port PORT           mc-visual-probe loopback port (default: 8766)
  --xvfb-screen SPEC          Xvfb screen geometry (default: 1920x1080x24)
  --real-renderer             Real LWJGL/OpenGL through Xvfb (default)
  --stub-renderer             HeadlessMC -lwjgl stub; screenshots will fail
  --agent PATH                Optional hmc-real-render-agent.jar fallback
  --validate-only             Run preflight checks without launching
  -h, --help                  Show this help

Equivalent environment variables:
  HMC_SERVER_ADDRESS, HMC_JAVA_BIN, HMC_LAUNCHER_JAR,
  HMC_MINECRAFT_VERSION, HMC_GAME_DIR, HMC_PROBE_PORT,
  HMC_XVFB_SCREEN, HMC_RENDER_MODE, HMC_REAL_RENDERER_AGENT
EOF
}

fail() {
  printf 'connect.bash: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf 'connect.bash: warning: %s\n' "$*" >&2
}

require_value() {
  (( $# >= 2 )) || fail "missing value for $1"
}

hmc_script_parent="${BASH_SOURCE[0]%/*}"
[[ "$hmc_script_parent" != "${BASH_SOURCE[0]}" ]] || hmc_script_parent='.'
hmc_script_dir="$(cd -- "$hmc_script_parent" && pwd -P)"
readonly hmc_script_dir

hmc_server_address="${HMC_SERVER_ADDRESS:-127.0.0.1:59916}"
hmc_java_bin="${HMC_JAVA_BIN:-}"
hmc_launcher_jar="${HMC_LAUNCHER_JAR:-${hmc_script_dir}/headlessmc-launcher.jar}"
hmc_minecraft_version="${HMC_MINECRAFT_VERSION:-1.21.11}"
hmc_probe_port="${HMC_PROBE_PORT:-8766}"
hmc_xvfb_screen="${HMC_XVFB_SCREEN:-1920x1080x24}"
hmc_render_mode="${HMC_RENDER_MODE:-real}"
hmc_real_renderer_agent="${HMC_REAL_RENDERER_AGENT:-}"
hmc_validate_only=false
hmc_positional_server=''

if [[ -n "${HMC_GAME_DIR:-}" ]]; then
  hmc_game_dir="$HMC_GAME_DIR"
elif [[ -n "${HOME:-}" ]]; then
  hmc_game_dir="${HOME}/.minecraft"
else
  fail 'HOME is unset; provide --game-dir or HMC_GAME_DIR'
fi

while (( $# > 0 )); do
  case "$1" in
    --server)
      require_value "$@"
      hmc_server_address="$2"
      shift 2
      ;;
    --java)
      require_value "$@"
      hmc_java_bin="$2"
      shift 2
      ;;
    --launcher)
      require_value "$@"
      hmc_launcher_jar="$2"
      shift 2
      ;;
    --minecraft-version)
      require_value "$@"
      hmc_minecraft_version="$2"
      shift 2
      ;;
    --game-dir)
      require_value "$@"
      hmc_game_dir="$2"
      shift 2
      ;;
    --probe-port)
      require_value "$@"
      hmc_probe_port="$2"
      shift 2
      ;;
    --xvfb-screen)
      require_value "$@"
      hmc_xvfb_screen="$2"
      shift 2
      ;;
    --agent)
      require_value "$@"
      hmc_real_renderer_agent="$2"
      shift 2
      ;;
    --real-renderer)
      hmc_render_mode=real
      shift
      ;;
    --stub-renderer)
      hmc_render_mode=stub
      shift
      ;;
    --validate-only)
      hmc_validate_only=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      if (( $# > 0 )); then
        [[ -z "$hmc_positional_server" && $# -eq 1 ]] || fail 'too many positional arguments'
        hmc_positional_server="$1"
      fi
      break
      ;;
    -*)
      fail "unknown option: $1"
      ;;
    *)
      [[ -z "$hmc_positional_server" ]] || fail 'only one positional host:port is allowed'
      hmc_positional_server="$1"
      shift
      ;;
  esac
done

if [[ -n "$hmc_positional_server" ]]; then
  hmc_server_address="$hmc_positional_server"
fi

case "$hmc_render_mode" in
  real|stub) ;;
  *) fail "HMC_RENDER_MODE must be 'real' or 'stub': ${hmc_render_mode}" ;;
esac

if [[ -z "$hmc_java_bin" ]]; then
  command -v java >/dev/null 2>&1 || fail 'Java was not found; set --java or HMC_JAVA_BIN'
  hmc_java_bin="$(command -v java)"
fi

[[ -x "$hmc_java_bin" ]] || fail "Java executable not found or not executable: ${hmc_java_bin}"
[[ -r "$hmc_launcher_jar" ]] || fail "Launcher JAR not found: ${hmc_launcher_jar}"
[[ "$hmc_minecraft_version" =~ ^[0-9A-Za-z._+-]+$ ]] || fail \
  "invalid Minecraft version: ${hmc_minecraft_version}"
[[ "$hmc_probe_port" =~ ^[0-9]+$ ]] || fail "invalid probe port: ${hmc_probe_port}"
(( 10#${hmc_probe_port} >= 1 && 10#${hmc_probe_port} <= 65535 )) || fail \
  "probe port must be between 1 and 65535: ${hmc_probe_port}"
[[ "$hmc_xvfb_screen" =~ ^[0-9]+x[0-9]+x(16|24|32)$ ]] || fail \
  "invalid Xvfb screen: ${hmc_xvfb_screen} (expected WIDTHxHEIGHTxDEPTH)"

if [[ "$hmc_server_address" =~ ^(\[[^][:space:]]+\]|[^:[:space:]]+):([0-9]{1,5})$ ]]; then
  hmc_server_port="${BASH_REMATCH[2]}"
else
  fail "invalid server address: ${hmc_server_address} (expected host:port)"
fi
(( 10#${hmc_server_port} >= 1 && 10#${hmc_server_port} <= 65535 )) || fail \
  "server port must be between 1 and 65535: ${hmc_server_port}"

hmc_java_version="$("$hmc_java_bin" -version 2>&1)" || fail "unable to run Java: ${hmc_java_bin}"
if [[ "$hmc_java_version" =~ version\ \"(1\.)?([0-9]+) ]]; then
  hmc_java_major="${BASH_REMATCH[2]}"
  (( hmc_java_major >= 21 )) || fail "Java 21 or newer is required; found Java ${hmc_java_major}"
else
  fail "unable to determine Java version from: ${hmc_java_version%%$'\n'*}"
fi

[[ -d "$hmc_game_dir" ]] || fail "Minecraft game directory does not exist: ${hmc_game_dir}"
hmc_game_dir="$(cd -- "$hmc_game_dir" && pwd -P)"
hmc_mod_dir="${hmc_game_dir}/mods"
[[ -d "$hmc_mod_dir" ]] || fail "Minecraft mods directory does not exist: ${hmc_mod_dir}"

shopt -s nullglob
hmc_fabric_api=("$hmc_mod_dir"/fabric-api-*.jar)
hmc_specifics=("$hmc_mod_dir"/hmc-specifics-"$hmc_minecraft_version"-*-fabric*.jar)
hmc_visual_probe=("$hmc_mod_dir"/mc-visual-probe-*.jar)
(( ${#hmc_fabric_api[@]} > 0 )) || fail "Fabric API is missing from ${hmc_mod_dir}"
(( ${#hmc_specifics[@]} > 0 )) || fail \
  "HMC-Specifics for Minecraft ${hmc_minecraft_version} is missing from ${hmc_mod_dir}"
(( ${#hmc_visual_probe[@]} > 0 )) || fail "mc-visual-probe is missing from ${hmc_mod_dir}"
(( ${#hmc_fabric_api[@]} == 1 )) || warn "multiple Fabric API jars found in ${hmc_mod_dir}"
(( ${#hmc_specifics[@]} == 1 )) || warn "multiple matching HMC-Specifics jars found in ${hmc_mod_dir}"
(( ${#hmc_visual_probe[@]} == 1 )) || warn "multiple Visual Probe jars found in ${hmc_mod_dir}"

if [[ -n "$hmc_real_renderer_agent" ]]; then
  [[ "$hmc_render_mode" == real ]] || fail '--agent is valid only with the real renderer'
  [[ -r "$hmc_real_renderer_agent" ]] || fail \
    "real-renderer agent not found: ${hmc_real_renderer_agent}"
  hmc_agent_parent="${hmc_real_renderer_agent%/*}"
  [[ "$hmc_agent_parent" != "$hmc_real_renderer_agent" ]] || hmc_agent_parent='.'
  hmc_agent_dir="$(cd -- "$hmc_agent_parent" && pwd -P)"
  hmc_agent_dependencies=("$hmc_agent_dir"/asm-*.jar)
  (( ${#hmc_agent_dependencies[@]} > 0 )) || fail \
    "the real-renderer agent requires its asm-*.jar beside it: ${hmc_agent_dir}"
fi

hmc_config="${hmc_script_dir}/HeadlessMC/config.properties"
if [[ -r "$hmc_config" ]]; then
  if grep -Eq '(^|[=;])[[:space:]]*[A-Za-z]:[/\\]' "$hmc_config"; then
    warn "${hmc_config} contains Windows paths; remove or replace them on Linux"
  fi
  grep -Eq '^hmc\.offline\.username=.+' "$hmc_config" || \
    warn "${hmc_config} has no offline username; HeadlessMC will use its default"
  grep -Eq '^hmc\.offline\.uuid=[0-9A-Fa-f-]{32,36}$' "$hmc_config" || \
    warn "${hmc_config} has no valid-looking offline UUID; verify the server identity"
else
  warn "${hmc_config} is missing; HeadlessMC will create it with default offline identity"
fi

hmc_options_file="${hmc_game_dir}/options.txt"
if [[ -r "$hmc_options_file" ]]; then
  grep -Fxq 'pauseOnLostFocus:false' "$hmc_options_file" || \
    warn "set pauseOnLostFocus:false in ${hmc_options_file}"
  grep -Fxq 'onboardAccessibility:false' "$hmc_options_file" || \
    warn "set onboardAccessibility:false in ${hmc_options_file}"
else
  warn "${hmc_options_file} does not exist yet; the first-run accessibility screen may interrupt quick-connect"
fi

if [[ "$hmc_render_mode" == real ]]; then
  command -v xvfb-run >/dev/null 2>&1 || fail 'xvfb-run is required for real rendering'
  command -v Xvfb >/dev/null 2>&1 || fail 'Xvfb is required for real rendering'
  command -v xauth >/dev/null 2>&1 || fail 'xauth is required by xvfb-run'
  command -v ps >/dev/null 2>&1 || fail 'ps (usually from procps) is required for HeadlessMC Xvfb detection'
fi

printf '%s\n' \
  "Java: ${hmc_java_bin} (major ${hmc_java_major})" \
  "Fabric ${hmc_minecraft_version} -> ${hmc_server_address}" \
  "Launcher: ${hmc_launcher_jar}" \
  "HeadlessMC state: ${hmc_script_dir}/HeadlessMC" \
  "Minecraft game dir: ${hmc_game_dir}" \
  "Minecraft mods: ${hmc_mod_dir}" \
  "Visual Probe: 127.0.0.1:${hmc_probe_port}" \
  "Rendering: $(if [[ "$hmc_render_mode" == real ]]; then printf 'real LWJGL/OpenGL via Xvfb (%s)' "$hmc_xvfb_screen"; else printf 'HeadlessMC LWJGL stub (no real PNG)'; fi)"

if [[ "$hmc_validate_only" == true ]]; then
  printf '%s\n' 'Validation passed; HeadlessMC was not launched.'
  exit 0
fi

hmc_command="launch fabric:${hmc_minecraft_version} -offline"
if [[ "$hmc_render_mode" == stub ]]; then
  hmc_command+=" -lwjgl"
  warn 'stub renderer selected: mc-visual-probe PNG capture is expected to fail'
fi
hmc_command+=" --game-args \"--quickPlayMultiplayer ${hmc_server_address}\""

hmc_java_args=(
  "-Dhmc.mcdir=${hmc_game_dir}"
  "-Dhmc.gamedir=${hmc_game_dir}"
  '-Dhmc.auto.download.specifics=false'
)

if [[ "$hmc_render_mode" == real ]]; then
  hmc_java_args+=( '-Dhmc.check.xvfb=true' )
  if [[ -n "$hmc_real_renderer_agent" ]]; then
    hmc_java_args+=( "-javaagent:${hmc_real_renderer_agent}" '-Dmcenv.hmc.forceRealLwjgl=true' )
  fi
fi

hmc_probe_option="-Dmc-visual-probe.port=${hmc_probe_port}"
export _JAVA_OPTIONS="${_JAVA_OPTIONS:+${_JAVA_OPTIONS} }${hmc_probe_option}"

cd -- "$hmc_script_dir"
if [[ "$hmc_render_mode" == real ]]; then
  exec xvfb-run -a -s "-screen 0 ${hmc_xvfb_screen} -nolisten tcp" \
    "$hmc_java_bin" "${hmc_java_args[@]}" -jar "$hmc_launcher_jar" --command "$hmc_command"
else
  exec "$hmc_java_bin" "${hmc_java_args[@]}" -jar "$hmc_launcher_jar" --command "$hmc_command"
fi
