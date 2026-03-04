## Problem Statement:

The App (feeld.apkm) does not run on Android 12. Officially, it targets Android 13 as a minimum.

```
# sha1sum of known APKM
dfc916fc7766f7b471f4f4f2f0a7c482f0836af3  feeld.apkm
```

I want to patch this app to run on Android 12.

When diagnosing an issue -- aside from the immediate issue -- consider a more general approach? would other aspects of the App etc be affected?

## Patch Logic

All logic is documented in PATCH_LOGIC.md

## Agents

The PATCH_LOGIC.md file should always be updated when there are changes made to the code

## File Map

### Core Scripts
- `01_install_deps.sh`: Installs all system dependencies (apktool, apksigner, zipalign, java).
- `02_patch.sh`: Main script. Unpacks, patches (manifest & smali), rebuilds, signs, and zipaligns the APKM.
- `03_install_device.sh`: Installs the patched APKM to a connected Android device.
- `rebuild_only.sh`: Helper script to just rebuild, sign, and install without re-unpacking (useful for iterating on smali changes).

### Patch Scripts (`scripts/`)
- `compat_api33.sh`: Orchestrates API 33 compatibility fixes (removes permissions, calls python patchers).
- `compat_api33_dispatcher.py`: Patches `OnBackInvokedDispatcher` calls (API 33+) to be safe on Android 12.
- `compat_api33_flags.py`: Handles API 33 specific flags.
- `fix_crash_9patch.py`: Fixes crashes caused by invalid 9-patch image chunks in resources.
- `fix_crash_photo_picker.py`: Fixes crash on Android 12 by patching `h/d$a.smali` to check SDK version before using `MediaStore.getPickImagesMaxLimit()`.
- `fix_crash_profileinstaller.py`: Fixes crashes related to `androidx.profileinstaller`.
- `fix_crash_rn_appsflyer.py`: Fixes crashes in AppsFlyer React Native module.
- `fix_crash_rn_textinput.py`: Fixes crashes in React Native TextInput (Material Design issue).
- `fix_drawables_broken.py`: Fixes references to broken or missing drawables.
- `fix_drawables_dummy.py`: Creates dummy drawable files to prevent `ResourceNotFoundException`.
- `fix_drawables_null.py`: Fixes `android:src="@null"` crashes on some Android versions.
- `fix_manifest.py`: Fixes malformed `meta-data` tags in `AndroidManifest.xml`.
- `fix_manifest_permissions.sh`: Cleans up permissions in `AndroidManifest.xml`.
- `fix_mediastore_limit.py`: (Alternative) Attempts to patch `getPickImagesMaxLimit` call directly.
- `fix_pending_intent.py`: Adds `FLAG_IMMUTABLE` to `PendingIntent` creation for Android 12+ compliance.
- `merge_resources.sh`: Merges resources from split APKs into the base APK.

### Documentation
- `PATCH_LOGIC.md`: Detailed documentation of the patching strategy and logic.
- `PROBLEM.md`: This file, describing the problem and file structure.
- `TEST_AUTOMATION.md`: Notes on test automation.
