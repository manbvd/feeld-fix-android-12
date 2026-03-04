#!/usr/bin/env python3
import os
import sys

def fix_manifest():
    manifest_path = "work/base_decoded/AndroidManifest.xml"
    if not os.path.exists(manifest_path):
        print(f"Error: {manifest_path} not found.")
        return False

    with open(manifest_path, "r") as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    removed = False

    # Target service block to remove:
    # <service ns0:exported="false" ns0:name="io.invertase.firebase.messaging.ReactNativeFirebaseMessagingService">
    #     <intent-filter>
    #         <action ns0:name="com.google.firebase.MESSAGING_EVENT" />
    #     </intent-filter>
    # </service>

    for line in lines:
        stripped = line.strip()
        if 'ns0:name="io.invertase.firebase.messaging.ReactNativeFirebaseMessagingService"' in stripped and '<service' in stripped:
            skip = True
            removed = True
            continue
        
        if skip:
            if '</service>' in stripped:
                skip = False
            continue
            
        new_lines.append(line)

    if removed:
        print("Removed duplicate service from AndroidManifest.xml")
        with open(manifest_path, "w") as f:
            f.writelines(new_lines)
        return True
    
    print("Warning: Could not find duplicate service in AndroidManifest.xml (might already be removed)")
    return False

def fix_smali():
    smali_path = "work/base_decoded/smali/co/feeld/CustomMessagingService.smali"
    if not os.path.exists(smali_path):
        print(f"Error: {smali_path} not found.")
        return False

    with open(smali_path, "r") as f:
        lines = f.readlines()
        
    new_lines = []
    in_method = False
    skip_original_implementation = False
    patched = False
    
    # We are looking for: .method public onMessageReceived(Lcom/google/firebase/messaging/T;)V
    
    for line in lines:
        if ".method public onMessageReceived" in line:
            in_method = True
            new_lines.append(line)
            
            # Inject our new implementation
            new_lines.append("    .locals 1\n")
            new_lines.append("\n")
            new_lines.append('    const-string v0, "remoteMessage"\n')
            new_lines.append("\n")
            new_lines.append("    invoke-static {p1, v0}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullParameter(Ljava/lang/Object;Ljava/lang/String;)V\n")
            new_lines.append("\n")
            new_lines.append("    # Patch: Try Braze first\n")
            new_lines.append("    sget-object v0, Lcom/braze/push/BrazeFirebaseMessagingService;->Companion:Lcom/braze/push/BrazeFirebaseMessagingService$Companion;\n")
            new_lines.append("\n")
            new_lines.append("    invoke-virtual {v0, p0, p1}, Lcom/braze/push/BrazeFirebaseMessagingService$Companion;->handleBrazeRemoteMessage(Landroid/content/Context;Lcom/google/firebase/messaging/T;)Z\n")
            new_lines.append("\n")
            new_lines.append("    move-result v0\n")
            new_lines.append("\n")
            new_lines.append("    # If Braze handled it (true), return immediately\n")
            new_lines.append("    if-eqz v0, :cond_skip_super\n")
            new_lines.append("    return-void\n")
            new_lines.append("\n")
            new_lines.append("    :cond_skip_super\n")
            new_lines.append("    # If not handled, call super (React Native)\n")
            new_lines.append("    invoke-super {p0, p1}, Lio/invertase/firebase/messaging/ReactNativeFirebaseMessagingService;->onMessageReceived(Lcom/google/firebase/messaging/T;)V\n")
            new_lines.append("\n")
            new_lines.append("    return-void\n")
            
            skip_original_implementation = True
            patched = True
            continue
            
        if in_method and ".end method" in line:
            in_method = False
            skip_original_implementation = False
            new_lines.append(line)
            continue
            
        if skip_original_implementation:
            continue
            
        new_lines.append(line)
        
    if patched:
        with open(smali_path, "w") as f:
            f.writelines(new_lines)
        print("Patched CustomMessagingService.smali")
        return True
    else:
        print("Warning: Could not find onMessageReceived in CustomMessagingService.smali")
        return False

if __name__ == "__main__":
    print("Applying FIX_NOTIFICATION_DUPLICATE patches...")
    fix_manifest()
    fix_smali()
