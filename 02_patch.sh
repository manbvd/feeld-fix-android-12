#!/usr/bin/env bash
# 02_patch.sh
# Unpacks, patches, rebuilds, signs, and repackages the Feeld APKM
# to lower minSdkVersion from 33 (Android 13) to 31 (Android 12).
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
APKM_IN="feeld.apkm"
KEYSTORE="patch.keystore"
KEY_ALIAS="feeldpatch"
KEY_PASS="feeldpatch"          # change if desired
STORE_PASS="feeldpatch"        # change if desired
TARGET_MIN_SDK=31              # Android 12

WORK_DIR="work"
EXTRACTED_DIR="$WORK_DIR/extracted"
DECODED_DIR="$WORK_DIR/base_decoded"
REBUILT_APK="$WORK_DIR/base_rebuilt.apk"
SIGNED_APK="$WORK_DIR/base_signed.apk"
ALIGNED_APK="$WORK_DIR/base_aligned.apk"
OUT_DIR="$WORK_DIR/out"
APKM_OUT="feeld_patched.apkm"
# ─────────────────────────────────────────────────────────────────────────────

echo "==> Step 1: Unpack APKM"
rm -rf "$WORK_DIR"
mkdir -p "$EXTRACTED_DIR"
unzip -q "$APKM_IN" -d "$EXTRACTED_DIR"
echo "    Contents:"
ls "$EXTRACTED_DIR"

echo ""
echo "==> Step 2: Decompile base.apk"
apktool d "$EXTRACTED_DIR/base.apk" -o "$DECODED_DIR" --force

echo ""
echo "==> Step 3: Patch AndroidManifest.xml (minSdkVersion -> $TARGET_MIN_SDK)"
MANIFEST="$DECODED_DIR/AndroidManifest.xml"

# --- MERGE SPLIT RESOURCES START ---
echo "==> Step 3b: Merge split resources (fix missing drawables)"
if [[ -x "$(dirname "$0")/scripts/merge_resources.sh" ]]; then
    "$(dirname "$0")/scripts/merge_resources.sh"
else
    echo "    [WARN] scripts/merge_resources.sh not found."
fi

echo "==> Step 3c: Create dummy drawables for missing icons"
if [[ -f "$(dirname "$0")/scripts/fix_drawables_dummy.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_drawables_dummy.py"
else
    echo "    [WARN] scripts/fix_drawables_dummy.py not found."
fi

echo "==> Step 3d: Fix broken drawables references"
if [[ -f "$(dirname "$0")/scripts/fix_drawables_broken.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_drawables_broken.py"
else
    echo "    [WARN] scripts/fix_drawables_broken.py not found."
fi

echo "==> Step 3e: Fix EditText background crash (invalid 9-patch)"
if [[ -f "$(dirname "$0")/scripts/fix_crash_9patch.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_crash_9patch.py"
else
    echo "    [WARN] scripts/fix_crash_9patch.py not found."
fi

echo "==> Step 3f: Fix ALL invalid @null drawables (prevents crashes on Android 12+)"
if [[ -f "$(dirname "$0")/scripts/fix_drawables_null.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_drawables_null.py"
else
    echo "    [WARN] scripts/fix_drawables_null.py not found."
fi

echo "==> Step 3g: Fix RN EditText Material crash"
if [[ -f "$(dirname "$0")/scripts/fix_crash_rn_textinput.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_crash_rn_textinput.py"
else
    echo "    [WARN] scripts/fix_crash_rn_textinput.py not found."
fi

echo "==> Step 3h: Fix Photo Picker crash (Android 12 compatibility)"
if [[ -f "$(dirname "$0")/scripts/fix_crash_photo_picker.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_crash_photo_picker.py"
else
    echo "    [WARN] scripts/fix_crash_photo_picker.py not found."
fi

echo "==> Step 3i: Fix findOnBackInvokedDispatcher crash"
if [[ -f "$(dirname "$0")/scripts/fix_crash_back_dispatcher_lookup.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_crash_back_dispatcher_lookup.py"
else
    echo "    [WARN] scripts/fix_crash_back_dispatcher_lookup.py not found."
fi

echo "==> Step 3j: Add Network Security Config (MITM Support)"
if [[ -f "$(dirname "$0")/scripts/add_network_security_config.py" ]]; then
    python3 "$(dirname "$0")/scripts/add_network_security_config.py"
else
    echo "    [WARN] scripts/add_network_security_config.py not found."
fi

echo "==> Step 3k: Fix Duplicate Notifications"
if [[ -f "$(dirname "$0")/scripts/fix_notifications.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_notifications.py"
else
    echo "    [WARN] scripts/fix_notifications.py not found."
fi

echo "==> Step 3l: Fix Location Dialog & Mock Detection"
if [[ -f "$(dirname "$0")/scripts/fix_location.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_location.py"
else
    echo "    [WARN] scripts/fix_location.py not found."
fi

# --- MERGE SPLIT RESOURCES END ---

# Show current sdk line before patching
echo "    Before:"
grep -i "minSdkVersion\|targetSdkVersion\|uses-sdk" "$MANIFEST" || true

# Patch minSdkVersion (handles both attribute forms)
sed -i "s/android:minSdkVersion=\"[0-9]*\"/android:minSdkVersion=\"$TARGET_MIN_SDK\"/" "$MANIFEST"

# Also patch apktool.yml so apktool doesn't override on rebuild
APKTOOL_YML="$DECODED_DIR/apktool.yml"
if [[ -f "$APKTOOL_YML" ]]; then
    sed -i "s/minSdkVersion: '[0-9]*'/minSdkVersion: '$TARGET_MIN_SDK'/" "$APKTOOL_YML"
    sed -i "s/minSdkVersion: [0-9]*/minSdkVersion: $TARGET_MIN_SDK/" "$APKTOOL_YML"
fi

echo "    After:"
grep -i "minSdkVersion\|targetSdkVersion\|uses-sdk" "$MANIFEST" || true

echo ""
echo "==> Step 4b: Auto-fixing Android 13 API compatibility issues..."

# 1. Permission fix
if [[ -x "$(dirname "$0")/scripts/fix_manifest_permissions.sh" ]]; then
    "$(dirname "$0")/scripts/fix_manifest_permissions.sh" "$MANIFEST"
else
     echo "    [WARN] scripts/fix_manifest_permissions.sh not found."
fi

# 2. OnBackInvokedDispatcher fix
if [[ -f "$(dirname "$0")/scripts/compat_api33_dispatcher.py" ]]; then
     echo "    Patching OnBackInvokedDispatcher calls..."
     python3 "$(dirname "$0")/scripts/compat_api33_dispatcher.py" "$DECODED_DIR"
else
     echo "    [WARN] scripts/compat_api33_dispatcher.py not found."
fi

# 3. Flags fix
if [[ -f "$(dirname "$0")/scripts/compat_api33_flags.py" ]]; then
     echo "    Patching PackageManager Flags calls..."
     python3 "$(dirname "$0")/scripts/compat_api33_flags.py" "$DECODED_DIR"
else
     echo "    [WARN] scripts/compat_api33_flags.py not found."
fi

echo "    Done fixing API 33 compatibility."

# 5. Disable Analytics
echo ""
echo "==> Step 4e: Disabling Analytics (FB, Firebase, Amplitude)"
if [[ -f "$(dirname "$0")/scripts/disable_analytics.py" ]]; then
    python3 "$(dirname "$0")/scripts/disable_analytics.py"
else
    echo "    [WARN] scripts/disable_analytics.py not found."
fi

echo ""
echo "==> Step 4c: Apply specific crash fixes (RNAppsFlyer, ProfileInstaller)"
if [[ -x "$(dirname "$0")/scripts/fix_crash_rn_appsflyer.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_crash_rn_appsflyer.py" "$DECODED_DIR/smali_classes2/com/appsflyer/reactnative/RNAppsFlyerModule.smali"
fi

if [[ -f "$(dirname "$0")/scripts/fix_crash_profileinstaller.py" ]]; then
    # We don't know exactly which smali folder it is in (smali, smali_classes2, etc), but find said smali/
    # Based on previous find command, it was in work/base_decoded/smali/
    TARGET_SMALI="$DECODED_DIR/smali/androidx/profileinstaller/h\$a.smali"
    if [[ -f "$TARGET_SMALI" ]]; then
        python3 "$(dirname "$0")/scripts/fix_crash_profileinstaller.py" "$TARGET_SMALI"
    else
        echo "    [WARN] Could not find androidx/profileinstaller/h\$a.smali"
    fi
fi

echo ""
echo "==> Step 4e: Fix PendingIntent mutability (Android 12+ crash)"
if [[ -f "$(dirname "$0")/scripts/fix_pending_intent.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_pending_intent.py" "$DECODED_DIR"
else
    echo "    [WARN] scripts/fix_pending_intent.py not found."
fi

echo ""
echo "==> Step 4d: Fix any malformed meta-data tags in manifest"
if [[ -x "$(dirname "$0")/scripts/fix_manifest.py" ]]; then
    python3 "$(dirname "$0")/scripts/fix_manifest.py" "$MANIFEST"
else
    echo "    [WARN] scripts/fix_manifest.py not found or not executable"
fi

echo ""
echo "==> Rebuilding, signing, and packaging..."
"$(dirname "$0")/03_rebuild.sh"

echo ""
echo "Install on device via SAI, or with ADB:"
echo "  adb install-multiple $OUT_DIR/*.apk"


