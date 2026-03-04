import sys
import os

def fix_default_error_screen(base_dir):
    """
    Fix PendingIntent.getActivity in DefaultErrorScreen.smali
    Change 0x10000000 -> 0x14000000 (FLAG_CANCEL_CURRENT | FLAG_IMMUTABLE)
    """
    target_file = os.path.join(base_dir, "smali_classes3/com/masteratul/exceptionhandler/DefaultErrorScreen.smali")
    if not os.path.exists(target_file):
        print(f"  [WARN] {target_file} not found.")
        return

    with open(target_file, 'r') as f:
        content = f.read()

    # Pattern to find the constant before getActivity call
    # const/high16 v2, 0x10000000
    # invoke-static {p0, v1, v0, v2}, Landroid/app/PendingIntent;->getActivity
    
    old_code = "const/high16 v2, 0x10000000"
    new_code = "const/high16 v2, 0x14000000"
    
    if old_code in content:
        # Check if it is followed by PendingIntent.getActivity nearby
        if "Landroid/app/PendingIntent;->getActivity" in content:
            print(f"  [INFO] Patching {target_file}...")
            content = content.replace(old_code, new_code)
            with open(target_file, 'w') as f:
                f.write(content)
        else:
            print(f"  [WARN] Found constant but not getActivity in {target_file}")
    else:
        print(f"  [WARN] Constant {old_code} not found in {target_file}")


def fix_force_stop_runnable(base_dir):
    """
    Fix PendingIntent.getBroadcast in ForceStopRunnable.smali
    Inject 'or-int/2addr p1, 0x4000000' (FLAG_IMMUTABLE)
    """
    target_file = os.path.join(base_dir, "smali/androidx/work/impl/utils/ForceStopRunnable.smali")
    if not os.path.exists(target_file):
        print(f"  [WARN] {target_file} not found.")
        return

    with open(target_file, 'r') as f:
        lines = f.readlines()

    new_lines = []
    in_method = False
    method_patched = False
    
    # We are looking for:
    # .method private static d(Landroid/content/Context;I)Landroid/app/PendingIntent;
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        if ".method private static d(Landroid/content/Context;I)Landroid/app/PendingIntent;" in line:
            in_method = True
            continue
            
        if in_method and ".locals" in line and not method_patched:
            # We are inside the method and just passed locals declaration.
            # Inject the fix here.
            
            # Add:
            # const/high16 v1, 0x4000000
            # or-int/2addr p1, v1
            
            print(f"  [INFO] Patching {target_file}...")
            new_lines.append("    const/high16 v1, 0x4000000\n")
            new_lines.append("    or-int/2addr p1, v1\n")
            method_patched = True
            in_method = False 

    if method_patched:
        with open(target_file, 'w') as f:
            f.writelines(new_lines)
    else:
        print(f"  [WARN] Could not patch {target_file}. Method signature not found?")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 fix_pending_intent.py <base_decoded_dir>")
        sys.exit(1)
        
    base_decoded_dir = sys.argv[1]
    
    print("Applying PendingIntent mutability fixes...")
    fix_default_error_screen(base_decoded_dir)
    fix_force_stop_runnable(base_decoded_dir)
    print("Done.")

if __name__ == "__main__":
    main()

