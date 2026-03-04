import re
import os

def disable_manifest_analytics(manifest_path):
    print(f"Processing {manifest_path}...")
    with open(manifest_path, 'r') as f:
        content = f.read()

    # Facebook
    content = re.sub(
        r'(<meta-data \w+:name="com\.facebook\.sdk\.AutoLogAppEventsEnabled" \w+:value=")[^"]*(" />)',
        r'\1false\2',
        content
    )
    content = re.sub(
        r'(<meta-data \w+:name="com\.facebook\.sdk\.AutoInitEnabled" \w+:value=")[^"]*(" />)',
        r'\1false\2',
        content
    )
    content = re.sub(
        r'(<meta-data \w+:name="com\.facebook\.sdk\.AdvertiserIDCollectionEnabled" \w+:value=")[^"]*(" />)',
        r'\1false\2',
        content
    )

    # Firebase / Google Analytics
    content = re.sub(
        r'(<meta-data \w+:name="firebase_analytics_collection_deactivated" \w+:value=")[^"]*(" />)',
        r'\1true\2',
        content
    )
    content = re.sub(
        r'(<meta-data \w+:name="firebase_analytics_collection_enabled" \w+:value=")[^"]*(" />)',
        r'\1false\2',
        content
    )
    content = re.sub(
        r'(<meta-data \w+:name="google_analytics_adid_collection_enabled" \w+:value=")[^"]*(" />)',
        r'\1false\2',
        content
    )
    content = re.sub(
        r'(<meta-data \w+:name="google_analytics_ssaid_collection_enabled" \w+:value=")[^"]*(" />)',
        r'\1false\2',
        content
    )
    # Add explicit disables if missing or ensure existing are false
    keys_to_disable = [
        "google_analytics_default_allow_analytics_storage",
        "google_analytics_default_allow_ad_storage",
        "google_analytics_default_allow_ad_user_data",
        "google_analytics_default_allow_ad_personalization_signals"
    ]
    for key in keys_to_disable:
        content = re.sub(
            f'(<meta-data \w+:name="{key}" \w+:value=")[^"]*(" />)',
            r'\1false\2',
            content
        )

    with open(manifest_path, 'w') as f:
        f.write(content)
    print("Manifest updated.")

def patch_fb_events(smali_path):
    if not os.path.exists(smali_path):
        print(f"File not found: {smali_path}")
        return

    print(f"Patching {smali_path}...")
    with open(smali_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_target_method = False
    skip_lines = False
    
    target_methods = [
        "logEvent",
        "logPushNotificationOpen",
        "setUserID",
        "setUserData",
        "flush"
    ]

    for line in lines:
        # Check for method start
        if line.strip().startswith(".method public"):
            for method in target_methods:
                if f" {method}(" in line:
                    in_target_method = True
                    new_lines.append(line)
                    # Add neutral implementation
                    new_lines.append("    .locals 0\n")
                    new_lines.append("    return-void\n")
                    skip_lines = True
                    break
            if not in_target_method:
                new_lines.append(line)
        elif line.strip().startswith(".end method") and in_target_method:
            in_target_method = False
            skip_lines = False
            new_lines.append(line)
        elif not skip_lines:
            new_lines.append(line)
            
    with open(smali_path, 'w') as f:
        f.writelines(new_lines)
    print("FBAppEventsLoggerModule patched.")

def patch_firebase_analytics(smali_path):
    if not os.path.exists(smali_path):
        print(f"File not found: {smali_path}")
        return

    print(f"Patching {smali_path}...")
    with open(smali_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_target_method = False
    skip_lines = False
    method_register_p = None

    # Methods that take a Promise as the last argument
    # We need to resolve it with null to avoid hanging JS
    target_methods = {
        "logEvent": 3, # (String, ReadableMap, Promise) -> p3 is promise
        "setUserId": 2, # (String, Promise) -> p2 is promise
        "setUserProperty": 3, # (String, String, Promise) -> p3 is promise
        "setAnalyticsCollectionEnabled": 2, # (Boolean, Promise) -> p2 is promise
        "resetAnalyticsData": 1, # (Promise) -> p1 is promise
        "setSessionTimeoutDuration": 3, # (Double, Promise) -> p3 is promise (Double takes 2 regs: p1, p2)
        "setDefaultEventParameters": 2, # (ReadableMap, Promise) -> p2 is promise
        "setConsent": 2 # (ReadableMap, Promise) -> p2 is promise
    }

    # Helper to check signature and get promise register
    def get_promise_register(line, method_name):
        # Scan argument types to determine register
        # Simplified logic based on known signatures from file analysis
        if method_name in target_methods:
             return f"p{target_methods[method_name]}"
        return None

    for line in lines:
        if line.strip().startswith(".method public"):
            found = False
            for method in target_methods:
                if f" {method}(" in line:
                    in_target_method = True
                    method_register_p = get_promise_register(line, method)
                    new_lines.append(line)
                    # Add implementation
                    new_lines.append("    .locals 1\n") # Minimal locals
                    new_lines.append("    const/4 v0, 0x0\n")
                    new_lines.append(f"    invoke-interface {{{method_register_p}, v0}}, Lcom/facebook/react/bridge/Promise;->resolve(Ljava/lang/Object;)V\n")
                    new_lines.append("    return-void\n")
                    skip_lines = True
                    found = True
                    break
            if not found:
                new_lines.append(line)
        elif line.strip().startswith(".end method") and in_target_method:
            in_target_method = False
            skip_lines = False
            new_lines.append(line)
        elif not skip_lines:
            new_lines.append(line)

    with open(smali_path, 'w') as f:
        f.writelines(new_lines)
    print("ReactNativeFirebaseAnalyticsModule patched.")

def main():
    base_dir = "work/base_decoded"

    # Adjust path if running from root or scripts dir
    if not os.path.exists(base_dir):
        print(f"Error: {base_dir} not found. Ensure you run this from the project root.")
        return

    # 1. Manifest
    manifest_path = os.path.join(base_dir, "AndroidManifest.xml")
    disable_manifest_analytics(manifest_path)

    # 2. FB App Events
    fb_smali = os.path.join(base_dir, "smali_classes2/com/facebook/reactnative/androidsdk/FBAppEventsLoggerModule.smali")
    patch_fb_events(fb_smali)

    # 3. Firebase Analytics
    firebase_smali = os.path.join(base_dir, "smali_classes4/io/invertase/firebase/analytics/ReactNativeFirebaseAnalyticsModule.smali")
    patch_firebase_analytics(firebase_smali)

    # 4. Amplitude (Skipped as logEvent not found in module, likely using legacy data migration only or different module)
    print("Amplitude patch skipped (logEvent not found in module).")

if __name__ == "__main__":
    main()
