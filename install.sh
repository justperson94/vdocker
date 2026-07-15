#!/bin/sh
# vdocker installer — downloads the latest release binary and installs it to your PATH.
#
#   curl -fsSL https://raw.githubusercontent.com/justperson94/vdocker/main/install.sh | sh
#
set -eu

REPO="justperson94/vdocker"
BINARY="vdocker"

info() { printf '\033[1;36m==>\033[0m %s\n' "$1"; }
err()  { printf '\033[1;31mError:\033[0m %s\n' "$1" >&2; exit 1; }

# --- Detect OS ---
os="$(uname -s)"
case "$os" in
    Linux)  os_name="linux" ;;
    Darwin) os_name="darwin" ;;
    *)      err "Unsupported OS: $os (only Linux and macOS are supported)" ;;
esac

# --- Detect architecture ---
arch="$(uname -m)"
case "$arch" in
    x86_64|amd64)  arch_name="amd64" ;;
    arm64|aarch64) arch_name="amd64" ;;  # macOS arm64 runs amd64 build via Rosetta
    *)             err "Unsupported architecture: $arch" ;;
esac

asset="${BINARY}-${os_name}-${arch_name}"
url="https://github.com/${REPO}/releases/latest/download/${asset}"

# --- Choose install directory ---
if [ -w "/usr/local/bin" ]; then
    install_dir="/usr/local/bin"
    sudo_cmd=""
elif [ -n "${HOME:-}" ]; then
    install_dir="${HOME}/.local/bin"
    sudo_cmd=""
    mkdir -p "$install_dir"
else
    install_dir="/usr/local/bin"
    sudo_cmd="sudo"
fi

# Fall back to sudo for /usr/local/bin if not writable and no HOME dir chosen
if [ "$install_dir" = "/usr/local/bin" ] && [ ! -w "/usr/local/bin" ]; then
    sudo_cmd="sudo"
fi

# --- Download ---
info "Downloading ${asset} ..."
tmp="$(mktemp)"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$tmp" "$url" || err "Download failed: $url"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$tmp" "$url" || err "Download failed: $url"
else
    err "Neither curl nor wget is available"
fi

# --- Install ---
chmod +x "$tmp"
info "Installing to ${install_dir}/${BINARY}"
$sudo_cmd mv "$tmp" "${install_dir}/${BINARY}"

# --- PATH check ---
case ":${PATH}:" in
    *":${install_dir}:"*) ;;
    *) printf '\033[1;33mNote:\033[0m %s is not on your PATH. Add this to your shell profile:\n  export PATH="%s:$PATH"\n' "$install_dir" "$install_dir" ;;
esac

# --- Shell completion (tab-complete container names for `vdocker exec`) ---
setup_completion() {
    cur_shell="$(basename "${SHELL:-}")"
    case "$cur_shell" in
        bash) rc="${HOME}/.bashrc"; line='eval "$(_VDOCKER_COMPLETE=bash_source vdocker)"' ;;
        zsh)  rc="${HOME}/.zshrc";  line='eval "$(_VDOCKER_COMPLETE=zsh_source vdocker)"' ;;
        *)    return ;;  # unsupported shell — skip silently
    esac

    # Already configured?
    if [ -e "$rc" ] && grep -qF "_VDOCKER_COMPLETE" "$rc" 2>/dev/null; then
        return
    fi

    if [ -w "$rc" ] || { [ ! -e "$rc" ] && [ -w "$(dirname "$rc")" ]; }; then
        printf '\n# vdocker shell completion\n%s\n' "$line" >> "$rc"
        info "Shell completion added to ${rc} (restart your shell to enable)"
    else
        printf '\033[1;33mNote:\033[0m Could not write %s. Add this line manually for tab-completion:\n  %s\n' "$rc" "$line"
    fi
}
setup_completion

info "Done! Run '${BINARY} --help' to get started."
