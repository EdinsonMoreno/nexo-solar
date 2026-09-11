#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-1.0.0}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR=".build/fedora-venv"
INSTALLER_DIR="dist/installers/fedora"

mkdir -p "$INSTALLER_DIR"

"$PYTHON_BIN" -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements.txt pyinstaller
"$VENV_DIR/bin/pyinstaller" --clean --noconfirm main_app.spec

if ! command -v rpmbuild >/dev/null 2>&1; then
    tar -C dist -czf "$INSTALLER_DIR/NexoSolar-Fedora-x86_64.tar.gz" "Nexo Solar"
    sha256sum "$INSTALLER_DIR/NexoSolar-Fedora-x86_64.tar.gz" > "$INSTALLER_DIR/SHA256SUMS.txt"
    echo "rpmbuild no esta disponible; se genero tar.gz instalable en $INSTALLER_DIR"
    exit 0
fi

RPM_TOPDIR="$PROJECT_ROOT/.build/rpmbuild"
mkdir -p "$RPM_TOPDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}

rpmbuild -bb packaging/fedora/nexo-solar.spec \
    --define "_topdir $RPM_TOPDIR" \
    --define "nexo_version $VERSION" \
    --define "project_root $PROJECT_ROOT"

find "$RPM_TOPDIR/RPMS" -type f -name '*.rpm' -exec cp {} "$INSTALLER_DIR/" \;
sha256sum "$INSTALLER_DIR"/*.rpm > "$INSTALLER_DIR/SHA256SUMS.txt"

echo "Paquete Fedora generado en $INSTALLER_DIR"
