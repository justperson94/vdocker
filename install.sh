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
PIP_HINT="install with: pip install git+https://github.com/${REPO}.git"
case "${os_name}-${arch}" in
    linux-x86_64|linux-amd64) arch_name="amd64" ;;
    darwin-arm64)             arch_name="arm64" ;;
    darwin-x86_64) err "No prebuilt binary for Intel macOS — $PIP_HINT" ;;
    linux-aarch64|linux-arm64) err "No prebuilt binary for Linux arm64 — $PIP_HINT" ;;
    *)             err "Unsupported architecture: $arch — $PIP_HINT" ;;
esac

asset="${BINARY}-${os_name}-${arch_name}.tar.gz"
url="https://github.com/${REPO}/releases/latest/download/${asset}"

# --- Choose install directories ---
# The binary ships as a directory (PyInstaller onedir) for fast startup:
# it goes under <prefix>/lib/vdocker and is symlinked into <prefix>/bin.
if [ -w "/usr/local/bin" ] && [ -w "/usr/local/lib" ]; then
    install_dir="/usr/local/bin"
    lib_dir="/usr/local/lib/${BINARY}"
    sudo_cmd=""
elif [ -n "${HOME:-}" ]; then
    install_dir="${HOME}/.local/bin"
    lib_dir="${HOME}/.local/lib/${BINARY}"
    sudo_cmd=""
    mkdir -p "$install_dir" "${HOME}/.local/lib"
else
    install_dir="/usr/local/bin"
    lib_dir="/usr/local/lib/${BINARY}"
    sudo_cmd="sudo"
fi

if [ "$install_dir" = "/usr/local/bin" ] && { [ ! -w "/usr/local/bin" ] || [ ! -w "/usr/local/lib" ]; }; then
    sudo_cmd="sudo"
fi

command -v tar >/dev/null 2>&1 || err "'tar' is required but not found"

# --- Download ---
info "Downloading ${asset} ..."
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT
tarball="${tmp_dir}/${asset}"
if command -v curl >/dev/null 2>&1; then
    curl -fsSL -o "$tarball" "$url" || err "Download failed: $url"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$tarball" "$url" || err "Download failed: $url"
else
    err "Neither curl nor wget is available"
fi

# --- Install ---
tar xzf "$tarball" -C "$tmp_dir" || err "Failed to extract $asset"
[ -x "${tmp_dir}/${BINARY}/${BINARY}" ] || err "Unexpected archive layout"

info "Installing to ${lib_dir}"
$sudo_cmd rm -rf "$lib_dir"
$sudo_cmd mkdir -p "$(dirname "$lib_dir")"
$sudo_cmd mv "${tmp_dir}/${BINARY}" "$lib_dir"
$sudo_cmd ln -sf "${lib_dir}/${BINARY}" "${install_dir}/${BINARY}"
info "Linked ${install_dir}/${BINARY}"

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
