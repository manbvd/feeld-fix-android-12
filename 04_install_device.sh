#!/usr/bin/env bash
# 03_install_device.sh
# Installs the patched APKM onto a connected Android device via ADB.
set -euo pipefail

OUT_DIR="work/out"
APKM_OUT="feeld_patched.apkm"

echo "==> Checking ADB connection..."
adb devices -l

# Confirm at least one device is connected (not just "List of devices attached")
DEVICE_COUNT=$(adb devices | tail -n +2 | grep -c "device$" || true)
if [[ "$DEVICE_COUNT" -eq 0 ]]; then
    echo "ERROR: No device connected. Connect your Android 12 device and enable USB debugging."
    exit 1
fi
echo "    $DEVICE_COUNT device(s) found."

echo ""
echo "==> Checking Android version on device..."
SDK=$(adb shell getprop ro.build.version.sdk 2>/dev/null | tr -d '[:space:]')
RELEASE=$(adb shell getprop ro.build.version.release 2>/dev/null | tr -d '[:space:]')
echo "    Android $RELEASE (API $SDK)"

# echo ""
# echo "==> Uninstalling previous version (if present)..."
# adb uninstall co.feeld 2>/dev/null || true
# sleep 1

echo ""
echo "==> Installing split APKs from $OUT_DIR ..."
# adb install-multiple handles split APKs natively
# shellcheck disable=SC2046
adb install-multiple $(ls "$OUT_DIR"/*.apk)

echo ""
echo "Installation complete."
echo "Launch Feeld on the device to verify."
