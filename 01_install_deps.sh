#!/usr/bin/env bash
# 01_install_deps.sh
# Installs all tools needed to patch the APK.
set -euo pipefail

echo "==> Updating package lists..."
sudo apt-get update -y

echo "==> Installing Java (required by apktool & keytool)..."
sudo apt-get install -y default-jdk

echo "==> Installing apktool..."
# Use the upstream wrapper script for the latest version
sudo apt-get install -y wget
wget -q https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool -O /tmp/apktool-wrapper
wget -q https://bitbucket.org/iBotPeaches/apktool/downloads/apktool_3.0.1.jar -O /tmp/apktool.jar
sudo install -m 755 /tmp/apktool-wrapper /usr/local/bin/apktool
sudo install -m 644 /tmp/apktool.jar /usr/local/lib/apktool.jar

echo "==> Installing zipalign & apksigner (Android build-tools)..."
sudo apt-get install -y zipalign apksigner

echo "==> Installing unzip, zip..."
sudo apt-get install -y unzip zip

echo "==> Verifying installations..."
java -version
apktool --version
zipalign --version 2>&1 | head -1 || true
apksigner --version 2>&1 | head -1 || true

echo ""
echo "All dependencies installed."
