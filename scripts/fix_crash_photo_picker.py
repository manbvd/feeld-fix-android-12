import os

# Target file based on previous investigation
target_file = "work/base_decoded/smali/h/d$a.smali"

if os.path.exists(target_file):
    with open(target_file, "r") as f:
        content = f.read()

    # The method currently looks like this:
    # .method public final d()Z
    #     .locals 0
    # 
    #     const/4 p0, 0x1
    # 
    #     return p0
    # .end method

    # We want to replace it with a version that checks if SDK_INT >= 33.
    # API 33 is Android 13.
    
    new_method = """
.method public final d()Z
    .locals 2

    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x21

    if-lt v0, v1, :cond_0

    const/4 v0, 0x1
    return v0

    :cond_0
    const/4 v0, 0x0
    return v0
.end method
"""

    start_marker = ".method public final d()Z"
    end_marker = ".end method"
    
    start_idx = content.find(start_marker)
    if start_idx != -1:
        end_idx = content.find(end_marker, start_idx)
        if end_idx != -1:
            end_idx += len(end_marker)
            original_method = content[start_idx:end_idx]
            
            # Sanity check: ensure the original method is small/simple as expected
            # to avoid replacing something else if obfuscation changed significantly (unlikely here)
            if "const/4 p0, 0x1" in original_method:
                print(f"Found target method in {target_file}. Applying patch...")
                new_content = content.replace(original_method, new_method.strip())
                with open(target_file, "w") as f:
                    f.write(new_content)
                print("Successfully patched photo picker check.")
            else:
                print("Warning: Method content did not match expected 'const/4 p0, 0x1'. Skipping.")
                print("Found content:", original_method)
        else:
            print("Could not find end of method d()")
    else:
        print(f"Could not find method d() in {target_file}")

else:
    print(f"File {target_file} not found. Is the APK decoded?")
