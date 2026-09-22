#!/usr/bin/env bash
# Install Blender on ai-workstation as the project's render node.
#
#   ssh ai-workstation 'bash -s' < ops/workstation/10-blender.sh
#
# Idempotent: re-running with the same version does nothing.
#
# DESIGN NOTES
#
# No sudo. This unpacks the official upstream tarball into ~/opt, so it
# touches nothing system-wide, needs no password over SSH, and uninstalls
# with `rm -rf`. It also keeps the machine reproducible from this repo
# rather than from someone's shell history.
#
# Pinned version, deliberately. The scene builder uses Blender's `bpy`
# API, which changes between releases. If the laptop and the workstation
# run different Blenders, the same script silently produces different
# scenes -- the worst kind of difference, because nothing errors. 4.2 LTS
# is chosen for a long-supported, stable API, and it has full OptiX
# support for the RTX 3090.
set -euo pipefail

VERSION="${BLENDER_VERSION:-4.2.9}"
SERIES="${VERSION%.*}"                       # 4.2.9 -> 4.2
PREFIX="${BLENDER_PREFIX:-$HOME/opt}"
TARBALL="blender-${VERSION}-linux-x64.tar.xz"
URL="https://download.blender.org/release/Blender${SERIES}/${TARBALL}"
DEST="${PREFIX}/blender-${VERSION}-linux-x64"
LINK="${PREFIX}/blender"

log() { printf '[10-blender] %s\n' "$*"; }

if [ -x "${DEST}/blender" ]; then
    log "already installed at ${DEST}"
    log "$("${DEST}/blender" --version 2>/dev/null | head -1)"
    exit 0
fi

mkdir -p "${PREFIX}"
cd "${PREFIX}"

log "downloading ${TARBALL}"
curl -fL --progress-bar -o "${TARBALL}" "${URL}"

# Verify against upstream's published checksum. A truncated download would
# otherwise surface much later as an obscure Blender crash.
log "verifying checksum"
if curl -fsSL "https://download.blender.org/release/Blender${SERIES}/${TARBALL}.sha256" \
        -o "${TARBALL}.sha256" 2>/dev/null; then
    sha256sum -c "${TARBALL}.sha256" || { log "CHECKSUM FAILED"; exit 1; }
    log "checksum OK"
else
    log "WARNING: no published .sha256 -- integrity NOT verified"
    log "         sha256 of what was downloaded:"
    sha256sum "${TARBALL}" | sed 's/^/           /'
fi

log "extracting"
tar -xJf "${TARBALL}"
rm -f "${TARBALL}" "${TARBALL}.sha256"

ln -sfn "${DEST}" "${LINK}"
log "symlink ${LINK} -> ${DEST}"

log "installed: $("${DEST}/blender" --version 2>/dev/null | head -1)"
log "bundled python: $("${DEST}/blender" -b --python-expr 'import sys;print("PYVER",sys.version.split()[0])' 2>/dev/null | grep -oP 'PYVER \K[0-9.]+' || echo unknown)"
log ""
log "add to PATH:  export PATH=\"${LINK}:\$PATH\""
