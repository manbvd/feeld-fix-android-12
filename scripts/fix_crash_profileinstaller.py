#!/usr/bin/env python3
import sys
import os

def patch_profileinstaller(smali_file):
    if not os.path.exists(smali_file):
        print(f"File not found: {smali_file}")
        sys.exit(1)

    with open(smali_file, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_method = False
    patched = False

    for line in lines:
        if ".method static a(Landroid/content/pm/PackageManager;Landroid/content/Context;)Landroid/content/pm/PackageInfo;" in line:
            in_method = True
            new_lines.append(line)
            continue
        
        if in_method:
            if ".locals 2" in line:
                new_lines.append("    .locals 4\n")
            elif "move-result-object p1" in line and not patched:
                new_lines.append(line)
                new_lines.append("\n    # PATCH: SDK_INT check for API 33\n")
                new_lines.append("    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n")
                new_lines.append("    const/16 v1, 0x21\n")
                new_lines.append("    if-lt v0, v1, :legacy_impl\n\n")
                
                # API 33 implementation (original code follows)
                new_lines.append("    :api33_impl\n")
            elif "const-wide/16 v0, 0x0" in line:
                # Mark where API 33 code starts to safely insert legacy jump target before it?
                # No, just keep going.
                new_lines.append(line)
            elif ".end method" in line:
                # Append legacy implementation at the end of the method
                new_lines.append("\n    :legacy_impl\n")
                new_lines.append("    const/4 v0, 0x0\n")
                # Using invoke-virtual because PackageManager is abstract, getPackageInfo(String, int) is usually virtual
                new_lines.append("    invoke-virtual {p0, p1, v0}, Landroid/content/pm/PackageManager;->getPackageInfo(Ljava/lang/String;I)Landroid/content/pm/PackageInfo;\n")
                new_lines.append("    move-result-object p0\n")
                new_lines.append("    return-object p0\n")
                new_lines.append(line)
                in_method = False
                patched = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if patched:
        with open(smali_file, 'w') as f:
            f.writelines(new_lines)
        print(f"Patched {smali_file}")
    else:
        print(f"Could not patch {smali_file} (method not found or already patched?)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 fix_profileinstaller.py <path_to_smali>")
        sys.exit(1)
    
    target_file = sys.argv[1]
    patch_profileinstaller(target_file)
