import os

def apply_patch():
    # 1. Disable Location Dialog in V4/f.smali
    f_smali_path = 'work/base_decoded/smali_classes2/V4/f.smali'
    if os.path.exists(f_smali_path):
        with open(f_smali_path, 'r') as file:
            content = file.read()
        
        # Determine unique context for replacement
        old_code_f = """    :goto_8
    new-instance v14, LV4/f;

    move-object v0, v14

    invoke-direct/range {v0 .. v13}, LV4/f;-><init>(LV4/b;JJFJDZZZ)V

    return-object v14"""
        
        new_code_f = """    :goto_8
    const/4 v11, 0x0

    new-instance v14, LV4/f;

    move-object v0, v14

    invoke-direct/range {v0 .. v13}, LV4/f;-><init>(LV4/b;JJFJDZZZ)V

    return-object v14"""

        if old_code_f in content:
            content = content.replace(old_code_f, new_code_f)
            with open(f_smali_path, 'w') as file:
                file.write(content)
            print(f"Patched {f_smali_path} (Disabled location dialog)")
        else:
            print(f"Skipped {f_smali_path} (Already patched or content mismatch)")
    else:
        print(f"File not found: {f_smali_path}")

    # 2. Disable Mock Detection in V4/h.smali
    h_smali_path = 'work/base_decoded/smali_classes2/V4/h.smali'
    if os.path.exists(h_smali_path):
        with open(h_smali_path, 'r') as file:
            content = file.read()
        
        old_code_h = """    const-string v1, "mocked"

    invoke-virtual {p0}, Landroid/location/Location;->isFromMockProvider()Z

    move-result p0"""
        
        new_code_h = """    const-string v1, "mocked"

    const/4 p0, 0x0"""

        if old_code_h in content:
            content = content.replace(old_code_h, new_code_h)
            with open(h_smali_path, 'w') as file:
                file.write(content)
            print(f"Patched {h_smali_path} (Disabled mock detection)")
        else:
            print(f"Skipped {h_smali_path} (Already patched or content mismatch)")
    else:
        print(f"File not found: {h_smali_path}")

if __name__ == "__main__":
    apply_patch()
