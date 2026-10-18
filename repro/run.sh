#!/bin/sh
# Reproduce the tail ledger. Requires Node.js v22.22.0 on PATH.
set -eu
cd "$(dirname "$0")/.."
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js v22.22.0 is required" >&2
  exit 1
fi
version=$(node -v)
if [ "$version" != "v22.22.0" ]; then
  echo "Node.js v22.22.0 is required, found $version" >&2
  exit 1
fi
if [ ! -d repro/node_modules/@permaweb/ao-loader ]; then
  npm ci --prefix repro
fi
exec node --max-old-space-size=8192 repro/run.mjs "$@"
