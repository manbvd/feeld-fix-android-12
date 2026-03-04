#!/usr/bin/env bash
set -euo pipefail

# Config
KEYSTORE="patch.keystore"
KEY_ALIAS="feeldpatch"
KEY_PASS="feeldpatch"
STORE_PASS="feeldpatch"
WORK_DIR="work"
EXTRACTED_DIR="$WORK_DIR/extracted"
DECODED_DIR="$WORK_DIR/base_decoded"
REBUILT_APK="$WORK_DIR/base_rebuilt.apk"
SIGNED_APK="$WORK_DIR/base_signed.apk"
ALIGNED_APK="$WORK_DIR/base_aligned.apk"
OUT_DIR="$WORK_DIR/out"
APKM_OUT="feeld_patched.apkm"

echo "==> Rebuilding base.apk"
apktool b "$DECODED_DIR" -o "$REBUILT_APK"

echo "==> Zipalign"
zipalign -f -v -p 4 "$REBUILT_APK" "$ALIGNED_APK"

echo "==> Signing"
if [[ ! -f "$KEYSTORE" ]]; then
    echo "    Generating keystore..."
    keytool -genkey -v \
        -keystore "$KEYSTORE" \
        -alias "$KEY_ALIAS" \
        -keyalg RSA -keysize 2048 \
        -validity 10000 \
        -storepass "$STORE_PASS" \
        -keypass "$KEY_PASS" \
        -dname "CN=Patch, OU=Patch, O=Patch, L=Patch, S=Patch, C=US"
fi

apksigner sign \
    --ks "$KEYSTORE" \
    --ks-key-alias "$KEY_ALIAS" \
    --ks-pass "pass:$STORE_PASS" \
    --key-pass "pass:$KEY_PASS" \
    --out "$SIGNED_APK" \
    "$ALIGNED_APK"

apksigner verify "$SIGNED_APK" && echo "    Signature OK"

echo "==> Signing splits"
mkdir -p "$OUT_DIR"
for split_apk in "$EXTRACTED_DIR"/split_*.apk; do
    if [[ -f "$split_apk" ]]; then
        split_name=$(basename "$split_apk")
        signed_split="$OUT_DIR/$split_name"
        echo "    Signing $split_name..."
        apksigner sign \
            --ks "$KEYSTORE" \
            --ks-key-alias "$KEY_ALIAS" \
            --ks-pass "pass:$STORE_PASS" \
            --key-pass "pass:$KEY_PASS" \
            --out "$signed_split" "$split_apk"
    fi
done

echo "==> Copying signed base.apk to output"
cp "$SIGNED_APK" "$OUT_DIR/base.apk"

echo "==> Creating patched APKM"
rm -f "$APKM_OUT"
(cd "$OUT_DIR" && zip -qr "../../$APKM_OUT" .)

echo "Done! Patched package: $APKM_OUT"
