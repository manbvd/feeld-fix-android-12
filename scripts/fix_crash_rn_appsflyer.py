#!/usr/bin/env python3
import sys
import os

def patch_rn_appsflyer(smali_file):
    if not os.path.exists(smali_file):
        print(f"File not found: {smali_file}")
        sys.exit(1)

    with open(smali_file, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_method = False
    method_name = "startSdk"
    patched = False

    for line in lines:
        # Detect start of method
        if f".method public {method_name}()V" in line:
            in_method = True
            new_lines.append(line)
            continue
        
        if in_method:
            # Add try_start after .locals
            if ".locals" in line:
                new_lines.append(line)
                new_lines.append("    :try_start_0\n")
            # Detect end of method to insert catch block
            elif ".end method" in line:
                new_lines.append("    :try_end_0\n")
                new_lines.append("    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0\n\n")
                new_lines.append("    :catch_0\n")
                new_lines.append("    move-exception v0\n")
                new_lines.append("    const-string v1, \"RNAppsFlyerPatch\"\n")
                new_lines.append("    const-string v2, \"Suppressed startSdk crash\"\n")
                new_lines.append("    invoke-static {v1, v2, v0}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I\n")
                new_lines.append("    return-void\n")
                new_lines.append(line) # .end method
                in_method = False
                patched = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if patched:
        with open(smali_file, 'w') as f:
            f.writelines(new_lines)
        print(f"Successfully patched {method_name} in {smali_file}")
    else:
        print(f"Could not find method {method_name} in {smali_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fix_rnappsflyer_crash.py <path_to_smali>")
        sys.exit(1)
    
    target_file = sys.argv[1]
    patch_rn_appsflyer(target_file)
