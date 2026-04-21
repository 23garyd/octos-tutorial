#!/usr/bin/env bash
# Build dora v1.0.0-rc.1 from source into a dedicated venv.
#
# Usage:
#   scripts/install_dora_v1.sh [--venv <path>] [--tag <git-tag>] [--src <path>]
#
# Defaults:
#   --venv  .venv-dora-v1
#   --tag   v1.0.0-rc.1
#   --src   .dora-src
#
# What it does:
#   1. Clones https://github.com/dora-rs/dora.git at the chosen tag.
#   2. cargo install --path binaries/cli --root <venv>  (puts `dora` in venv/bin)
#   3. maturin develop --release inside apis/python/node (installs dora Python pkg).

set -euo pipefail

VENV=".venv-dora-v1"
TAG="v1.0.0-rc.1"
SRC=".dora-src"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv) VENV="$2"; shift 2 ;;
    --tag)  TAG="$2";  shift 2 ;;
    --src)  SRC="$2";  shift 2 ;;
    -h|--help)
      sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1" >&2; exit 1; }; }
need git
need cargo
need python3

echo ">>> venv: $VENV"
if [[ ! -d "$VENV" ]]; then
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1090
source "$VENV/bin/activate"

# maturin refuses to run if both VIRTUAL_ENV and CONDA_PREFIX are set (it cannot
# tell which environment to install into). Drop the conda vars so maturin sees
# only our venv.
unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_SHLVL CONDA_PROMPT_MODIFIER CONDA_PYTHON_EXE 2>/dev/null || true

python -m pip install --upgrade pip maturin >/dev/null

echo ">>> clone/update dora source at $SRC (tag $TAG)"
if [[ ! -d "$SRC/.git" ]]; then
  git clone --depth 1 --branch "$TAG" https://github.com/dora-rs/dora.git "$SRC"
else
  git -C "$SRC" fetch --depth 1 origin tag "$TAG"
  git -C "$SRC" checkout "$TAG"
fi

echo ">>> cargo install dora CLI into $VENV/bin"
cargo install --path "$SRC/binaries/cli" --locked --root "$(realpath "$VENV")"

echo ">>> maturin develop dora Python bindings"
pushd "$SRC/apis/python/node" >/dev/null
maturin develop --release
popd >/dev/null

echo
echo ">>> verify"
"$VENV/bin/dora" --version
python -c "import dora; print('dora module:', dora.__file__)"
echo
echo "Note: the CLI reports as 'dora-cli 0.2.1' because the v1.0.0-rc.1 tag"
echo "has not yet bumped the workspace crate version to 1.0. The binary"
echo "itself is built from the v1.0.0-rc.1 source tree."
echo
echo "Activate with: source $VENV/bin/activate"
