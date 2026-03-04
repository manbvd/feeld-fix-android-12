import os
import re

def fix_toolbar_e():
    path = "work/base_decoded/smali/androidx/appcompat/widget/Toolbar$e.smali"
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        return

    with open(path, "r") as f:
        content = f.read()

    # Increase locals
    if "locals 0" in content:
        content = re.sub(
            r"(\.method static a\(Landroid/view/View;\)Ljava/lang/Object;\s+\.locals )0",
            r"\1 2",
            content
        )
    
    # Patch call
    # We use a unique label suffix to avoid conflicts if used multiple times (though unlikely here)
    patch = """
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x21
    if-lt v0, v1, :cond_api33_toolbar
    invoke-virtual {p0}, Landroid/view/View;->findOnBackInvokedDispatcher()Ljava/lang/Object;
    move-result-object p0
    goto :end_api33_toolbar
    :cond_api33_toolbar
    const/4 p0, 0x0
    :end_api33_toolbar
    """
    
    pattern = r"invoke-virtual \{p0\}, Landroid/view/View;->findOnBackInvokedDispatcher\(\)Ljava/lang/Object;\s+move-result-object p0"
    
    if re.search(pattern, content):
        content = re.sub(pattern, patch.strip(), content)
        with open(path, "w") as f:
            f.write(content)
        print(f"Patched {path}")
    else:
        print(f"Pattern not found in {path}")

def fix_u0_m_a():
    path = "work/base_decoded/smali/u0/m$a.smali"
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        return

    with open(path, "r") as f:
        content = f.read()
    
    # Increase locals for d() and e()
    content = re.sub(
        r"(\.method public static final ([de])\(Landroid/view/View;Ljava/lang/Object;\)V\s+\.locals )1",
        r"\1 2",
        content
    )

    # Patch call (appears twice, once in d, once in e)
    # Both use p0 for View and move result to p0.
    patch = """
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x21
    if-lt v0, v1, :cond_api33_u0
    invoke-virtual {p0}, Landroid/view/View;->findOnBackInvokedDispatcher()Ljava/lang/Object;
    move-result-object p0
    goto :end_api33_u0
    :cond_api33_u0
    const/4 p0, 0x0
    :end_api33_u0
    """
    
    pattern = r"invoke-virtual \{p0\}, Landroid/view/View;->findOnBackInvokedDispatcher\(\)Ljava/lang/Object;\s+move-result-object p0"
    
    if re.search(pattern, content):
        content = re.sub(pattern, patch.strip(), content)
        with open(path, "w") as f:
            f.write(content)
        print(f"Patched {path}")
    else:
        print(f"Pattern not found in {path}")

def fix_dc_c_b():
    path = "work/base_decoded/smali_classes3/dc/c$b.smali"
    if not os.path.exists(path):
        print(f"Skipping {path} (not found)")
        return
        
    with open(path, "r") as f:
        content = f.read()

    # Increase locals for a() and b()
    # a(Landroid/view/View;)V .locals 1 -> 2
    content = re.sub(r"(\.method public a\(Landroid/view/View;\)V\s+\.locals )1", r"\1 2", content)
    # b(Ldc/b;Landroid/view/View;Z)V .locals 1 -> 2
    content = re.sub(r"(\.method public b\(Ldc/b;Landroid/view/View;Z\)V\s+\.locals )1", r"\1 2", content)

    # Patch method a() using p1
    patch_a = """
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x21
    if-lt v0, v1, :cond_api33_dc_a
    invoke-virtual {p1}, Landroid/view/View;->findOnBackInvokedDispatcher()Ljava/lang/Object;
    move-result-object p1
    goto :end_api33_dc_a
    :cond_api33_dc_a
    const/4 p1, 0x0
    :end_api33_dc_a
    """
    content = re.sub(
        r"invoke-virtual \{p1\}, Landroid/view/View;->findOnBackInvokedDispatcher\(\)Ljava/lang/Object;\s+move-result-object p1",
        patch_a.strip(),
        content
    )
    
    # Patch method b() using p2
    patch_b = """
    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
    const/16 v1, 0x21
    if-lt v0, v1, :cond_api33_dc_b
    invoke-virtual {p2}, Landroid/view/View;->findOnBackInvokedDispatcher()Ljava/lang/Object;
    move-result-object p2
    goto :end_api33_dc_b
    :cond_api33_dc_b
    const/4 p2, 0x0
    :end_api33_dc_b
    """
    content = re.sub(
        r"invoke-virtual \{p2\}, Landroid/view/View;->findOnBackInvokedDispatcher\(\)Ljava/lang/Object;\s+move-result-object p2",
        patch_b.strip(),
        content
    )

    with open(path, "w") as f:
        f.write(content)
    print(f"Patched {path}")

if __name__ == "__main__":
    fix_toolbar_e()
    fix_u0_m_a()
    fix_dc_c_b()
