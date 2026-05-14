# Fix Feeld App for Android 12

The Feeld app targets Android 13 (API 33) as its minimum and uses APIs that don't exist on Android 12, causing it to crash immediately on launch. This project patches the app to run on Android 12 (API 31).

## What Gets Patched

- **Android 13+ API calls** — back-navigation, photo picker, and package manager calls are guarded with version checks so they are skipped on Android 12
- **Crash fixes** — several third-party SDKs (AppsFlyer, Braze, ProfileInstaller) crash on startup; these are patched individually
- **PendingIntent mutability** — Android 12 requires explicit `FLAG_IMMUTABLE` on `PendingIntent`; missing flags are injected
- **Resource issues** — split APK resources (drawables, icons) are merged into the base APK so nothing goes missing at runtime
- **Location dialog** — suppresses the forced "enable location" system dialog on every launch
- **Duplicate notifications** — deduplication fix applied
- **Analytics disabled** — Facebook, Firebase, and Amplitude analytics calls are removed

The app is re-signed with a local self-signed key. On Samsung devices with Knox, it may land in the work profile — it still works fine from there.

## Supported Version

Tested against **Feeld v8.9.3** (downloaded from APKMirror):

```
dfc916fc7766f7b471f4f4f2f0a7c482f0836af3  feeld.apkm
```

[Download from APKMirror](https://www.apkmirror.com/apk/feeld-ltd/feeld-meet-couples-singles/feeld-open-minded-dating-app-8-9-3-release/feeld-open-minded-dating-app-8-9-3-android-apk-download/)

## Requirements

Linux (Debian/Ubuntu). Run the dependency installer once:

```bash
./01_install_deps.sh
```

This installs: Java, `apktool`, `zipalign`, `apksigner`, `unzip`, and `zip`.

## Usage

1. Place `feeld.apkm` in the project directory (SHA1 above).
2. Run the patch script:

```bash
./02_patch.sh
```

This produces `feeld_patched.apkm` and the individual split APKs under `work/out/`.

3. Install on a connected Android 12 device:

```bash
./04_install_device.sh
```

Or install manually using [SAI (Split APKs Installer)](https://github.com/Aefyr/SAI) by copying `feeld_patched.apkm` to your device, or via ADB:

```bash
adb install-multiple work/out/*.apk
```

## Technical Details

See [PATCH_LOGIC.md](./PATCH_LOGIC.md) for a full breakdown of each patch layer and the reasoning behind it.
