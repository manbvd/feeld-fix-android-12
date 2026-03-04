#!/usr/bin/env bash
# scripts/fix_manifest_permissions.sh
# Removes permissions that are not supported or cause issues on older Android versions.
set -euo pipefail

MANIFEST="${1:-}"

if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: Manifest file not found: $MANIFEST"
    exit 1
fi

echo "    Removing POST_NOTIFICATIONS permission from manifest..."
sed -i '/<uses-permission[[:space:]]*android:name="android\.permission\.POST_NOTIFICATIONS"[[:space:]]*\/>/d' "$MANIFEST"
