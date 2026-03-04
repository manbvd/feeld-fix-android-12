#!/usr/bin/env python3
"""
patch_smali_api33.py — Patch smali files to guard API 33+ calls
(OnBackInvokedDispatcher) so the app doesn't crash on Android 12.

Usage: python3 patch_smali_api33.py <decoded_dir>
"""

import os
import sys
import re
from pathlib import Path

MIN_API = 33  # 0x21 in hex

def read(path: str) -> str:
    with open(path, "r") as f:
        return f.read()

def write(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)

def patch_count_msg(name: str, count: int) -> str:
    return f"    [{name}] {count} patch(es) applied"

# ─────────────────────────────────────────────────────────────────────────────
# Patch 0: Generic field type replacement
#   Replace field declarations with OnBackInvoked* types with Object to avoid
#   class loading errors on API < 33 (type resolution fails at class load time).
# ─────────────────────────────────────────────────────────────────────────────
def patch_field_types(decoded: str) -> int:
    """Replace OnBackInvoked* types with Object in all smali files (fields, methods, etc.)."""
    count = 0
    smali_dirs = []
    for entry in os.listdir(decoded):
        full = os.path.join(decoded, entry)
        if os.path.isdir(full) and entry.startswith("smali"):
            smali_dirs.append(full)

    for smali_dir in smali_dirs:
        for root, _, files in os.walk(smali_dir):
            for fname in files:
                if not fname.endswith(".smali"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = read(fpath)
                except Exception:
                    continue

                original = content
                
                # Replace field declarations with OnBackInvokedCallback type
                content = re.sub(
                    r'\.field ([^:]*):Landroid/window/OnBackInvokedCallback;',
                    r'.field \1:Ljava/lang/Object;',
                    content
                )
                # Replace field declarations with OnBackInvokedDispatcher type
                content = re.sub(
                    r'\.field ([^:]*):Landroid/window/OnBackInvokedDispatcher;',
                    r'.field \1:Ljava/lang/Object;',
                    content
                )
                
                # Replace field access type signatures (iget/iput-object)
                # e.g., "->fieldName:Landroid/window/OnBackInvokedDispatcher;" -> "->fieldName:Ljava/lang/Object;"
                content = re.sub(
                    r'(->[\w$]+):Landroid/window/OnBackInvokedCallback;',
                    r'\1:Ljava/lang/Object;',
                    content
                )
                content = re.sub(
                    r'(->[\w$]+):Landroid/window/OnBackInvokedDispatcher;',
                    r'\1:Ljava/lang/Object;',
                    content
                )
                
                # Replace method parameter and return types ONLY
                # (NOT in .implements or .annotation statements)
                # Split by lines and process carefully
                lines = content.split('\n')
                new_lines = []
                for line in lines:
                    # Skip .implements and .annotation.value lines 
                    if line.strip().startswith('.implements') or \
                       line.strip().startswith('.annotation') or \
                       line.strip().startswith('value ='):
                        new_lines.append(line)
                    else:
                        # Replace in method signatures, parameters, returns
                        line = re.sub(
                            r'Landroid/window/OnBackInvokedCallback;',
                            r'Ljava/lang/Object;',
                            line
                        )
                        line = re.sub(
                            r'Landroid/window/OnBackInvokedDispatcher;',
                            r'Ljava/lang/Object;',
                            line
                        )
                        new_lines.append(line)
                
                content = '\n'.join(new_lines)

                if content != original:
                    write(fpath, content)
                    count += 1

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Patch 0b: Remove problematic interface implementations
#   Classes like androidx.activity.D implement OnBackInvokedCallback, which
#   doesn't exist on API < 33. Removing the .implements lets the class load.
# ─────────────────────────────────────────────────────────────────────────────
def patch_remove_interfaces(decoded: str) -> int:
    """Remove .implements Landroid/window/OnBackInvoked* from classes."""
    count = 0
    smali_dirs = []
    for entry in os.listdir(decoded):
        full = os.path.join(decoded, entry)
        if os.path.isdir(full) and entry.startswith("smali"):
            smali_dirs.append(full)

    for smali_dir in smali_dirs:
        for root, _, files in os.walk(smali_dir):
            for fname in files:
                if not fname.endswith(".smali"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = read(fpath)
                except Exception:
                    continue

                original = content
                # Remove .implements lines that reference OnBackInvoked* types
                content = re.sub(
                    r'\.implements Landroid/window/OnBackInvokedCallback;\n',
                    '',
                    content
                )
                content = re.sub(
                    r'\.implements Landroid/window/OnBackInvokedDispatcher;\n',
                    '',
                    content
                )

                if content != original:
                    write(fpath, content)
                    count += 1

    return count


# ─────────────────────────────────────────────────────────────────────────────
# Patch 1: androidx/appcompat/app/h$l.smali — method a()
#   Static helper that directly calls Activity.getOnBackInvokedDispatcher().
#   Return null on API < 33.
# ─────────────────────────────────────────────────────────────────────────────
def patch_h_dollar_l(decoded: str) -> int:
    path = os.path.join(decoded, "smali/androidx/appcompat/app/h$l.smali")
    if not os.path.isfile(path):
        print(f"    [h$l] SKIP — file not found")
        return 0

    # Also handle the case where the file was already patched to .locals 1 by a previous
    # (buggy) run — match both .locals 0 and .locals 1/2 for the old pattern.
    old = (
        ".method static a(Landroid/app/Activity;)Landroid/window/OnBackInvokedDispatcher;\n"
        "    .locals 0\n"
        "\n"
        "    invoke-virtual {p0}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object p0\n"
        "\n"
        "    return-object p0\n"
        ".end method"
    )

    new = (
        ".method static a(Landroid/app/Activity;)Landroid/window/OnBackInvokedDispatcher;\n"
        "    .locals 2\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v1, 0x21\n"
        "\n"
        "    if-ge v0, v1, :api33_ok_hl_a\n"
        "\n"
        "    const/4 v0, 0x0\n"
        "\n"
        "    return-object v0\n"
        "\n"
        "    :api33_ok_hl_a\n"
        "    # --- end guard ---\n"
        "\n"
        "    invoke-virtual {p0}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object p0\n"
        "\n"
        "    return-object p0\n"
        ".end method"
    )

    content = read(path)
    if old not in content:
        print(f"    [h$l.a] SKIP — exact match not found (already patched?)")
        return 0
    content = content.replace(old, new)
    write(path, content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 2: androidx/appcompat/app/h.smali — method N()
#   Manages OnBackInvokedDispatcher for AppCompat delegate.
#   Return-void early on API < 33.
# ─────────────────────────────────────────────────────────────────────────────
def patch_h_method_N(decoded: str) -> int:
    path = os.path.join(decoded, "smali/androidx/appcompat/app/h.smali")
    if not os.path.isfile(path):
        print(f"    [h.N] SKIP — file not found")
        return 0

    old = (
        ".method public N(Landroid/window/OnBackInvokedDispatcher;)V\n"
        "    .locals 2\n"
        "\n"
        "    invoke-super {p0, p1}, Landroidx/appcompat/app/f;->N(Landroid/window/OnBackInvokedDispatcher;)V"
    )

    new = (
        ".method public N(Landroid/window/OnBackInvokedDispatcher;)V\n"
        "    .locals 2\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v1, 0x21\n"
        "\n"
        "    if-ge v0, v1, :api33_ok_h_N\n"
        "\n"
        "    return-void\n"
        "\n"
        "    :api33_ok_h_N\n"
        "    # --- end guard ---\n"
        "\n"
        "    invoke-super {p0, p1}, Landroidx/appcompat/app/f;->N(Landroid/window/OnBackInvokedDispatcher;)V"
    )

    content = read(path)
    if old not in content:
        print(f"    [h.N] SKIP — exact match not found (already patched?)")
        return 0
    content = content.replace(old, new)
    write(path, content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 3: androidx/appcompat/app/h.smali — method e1()
#   Calls h$l.b() and h$l.c() which use OnBackInvoked* types.
#   Return-void early on API < 33.
# ─────────────────────────────────────────────────────────────────────────────
def patch_h_method_e1(decoded: str) -> int:
    path = os.path.join(decoded, "smali/androidx/appcompat/app/h.smali")
    if not os.path.isfile(path):
        print(f"    [h.e1] SKIP — file not found")
        return 0

    old = (
        ".method e1()V\n"
        "    .locals 2\n"
        "\n"
        "    invoke-virtual {p0}, Landroidx/appcompat/app/h;->X0()Z"
    )

    new = (
        ".method e1()V\n"
        "    .locals 2\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v1, 0x21\n"
        "\n"
        "    if-ge v0, v1, :api33_ok_h_e1\n"
        "\n"
        "    return-void\n"
        "\n"
        "    :api33_ok_h_e1\n"
        "    # --- end guard ---\n"
        "\n"
        "    invoke-virtual {p0}, Landroidx/appcompat/app/h;->X0()Z"
    )

    content = read(path)
    if old not in content:
        print(f"    [h.e1] SKIP — exact match not found (already patched?)")
        return 0
    content = content.replace(old, new)
    write(path, content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 4: androidx/activity/j$b.smali — method a()
#   Kotlin wrapper calling Activity.getOnBackInvokedDispatcher().
#   Return null on API < 33.
# ─────────────────────────────────────────────────────────────────────────────
def patch_j_dollar_b(decoded: str) -> int:
    path = os.path.join(decoded, "smali/androidx/activity/j$b.smali")
    if not os.path.isfile(path):
        print(f"    [j$b] SKIP — file not found")
        return 0

    old = (
        ".method public final a(Landroid/app/Activity;)Landroid/window/OnBackInvokedDispatcher;\n"
        "    .locals 0\n"
        "\n"
        "    const-string p0, \"activity\"\n"
        "\n"
        "    invoke-static {p1, p0}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullParameter(Ljava/lang/Object;Ljava/lang/String;)V\n"
        "\n"
        "    invoke-virtual {p1}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object p0\n"
        "\n"
        "    const-string p1, \"activity.getOnBackInvokedDispatcher()\"\n"
        "\n"
        "    invoke-static {p0, p1}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullExpressionValue(Ljava/lang/Object;Ljava/lang/String;)V\n"
        "\n"
        "    return-object p0\n"
        ".end method"
    )

    new = (
        ".method public final a(Landroid/app/Activity;)Landroid/window/OnBackInvokedDispatcher;\n"
        "    .locals 1\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 p0, 0x21\n"
        "\n"
        "    if-ge v0, p0, :api33_ok_jb_a\n"
        "\n"
        "    const/4 p0, 0x0\n"
        "\n"
        "    return-object p0\n"
        "\n"
        "    :api33_ok_jb_a\n"
        "    # --- end guard ---\n"
        "\n"
        "    const-string p0, \"activity\"\n"
        "\n"
        "    invoke-static {p1, p0}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullParameter(Ljava/lang/Object;Ljava/lang/String;)V\n"
        "\n"
        "    invoke-virtual {p1}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object p0\n"
        "\n"
        "    const-string p1, \"activity.getOnBackInvokedDispatcher()\"\n"
        "\n"
        "    invoke-static {p0, p1}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullExpressionValue(Ljava/lang/Object;Ljava/lang/String;)V\n"
        "\n"
        "    return-object p0\n"
        ".end method"
    )

    content = read(path)
    if old not in content:
        print(f"    [j$b.a] SKIP — exact match not found (already patched?)")
        return 0
    content = content.replace(old, new)
    write(path, content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 4b: androidx/activity/j.smali — method n()
#   Lifecycle callback that calls C.o() with dispatcher on ON_CREATE.
#   Skip the C.o() call on API < 33 to prevent null parameter error.
# ─────────────────────────────────────────────────────────────────────────────
def patch_j_method_n(decoded: str) -> int:
    path = os.path.join(decoded, "smali/androidx/activity/j.smali")
    if not os.path.isfile(path):
        print(f"    [j.n] SKIP — file not found")
        return 0

    content = read(path)
    
    # Check if already patched
    if "if-lt v0, v1, :cond_0" in content and "API 33 guard" in content:
        print(f"    [j.n] SKIP — already patched")
        return 0

    # Find and patch the method using regex to be more flexible
    # We only need to patch the exact spot where C.o(p1) is called
    pattern = (
        r"(    if-ne p3, p2, :cond_0\n)"
        r"(\n    sget-object p2, Landroidx/activity/j\$b;->a:Landroidx/activity/j\$b;)"
    )
    
    replacement = (
        r"\1"
        r"    # --- API 33 guard (patched) ---\n"
        r"    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        r"\n"
        r"    const/16 v1, 0x21\n"
        r"\n"
        r"    if-lt v0, v1, :cond_0\n"
        r"    # --- end guard ---\n"
        r"\2"
    )
    
    # Also need to update .locals 1 -> .locals 2
    content = re.sub(
        r"(\.method private static final n\(Landroidx/activity/C;Landroidx/activity/j;Landroidx/lifecycle/u;Landroidx/lifecycle/l\$a;\)V\n)    \.locals 1",
        r"\1    .locals 2",
        content
    )
    
    # Apply the guard pattern
    new_content = re.sub(pattern, replacement, content)
    
    if new_content == content:
        print(f"    [j.n] SKIP — pattern not found")
        return 0
    
    write(path, new_content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 5: androidx/activity/q.smali — onCreate()
#   ComponentDialog.onCreate calls Dialog.getOnBackInvokedDispatcher().
#   Skip the back-invoked-dispatcher block on API < 33.
# ─────────────────────────────────────────────────────────────────────────────
def patch_q_oncreate(decoded: str) -> int:
    path = os.path.join(decoded, "smali/androidx/activity/q.smali")
    if not os.path.isfile(path):
        print(f"    [q.onCreate] SKIP — file not found")
        return 0

    old = (
        "    iget-object v0, p0, Landroidx/activity/q;->onBackPressedDispatcher:Landroidx/activity/C;\n"
        "\n"
        "    invoke-virtual {p0}, Landroid/app/Dialog;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object v1\n"
        "\n"
        "    const-string v2, \"onBackInvokedDispatcher\"\n"
        "\n"
        "    invoke-static {v1, v2}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullExpressionValue(Ljava/lang/Object;Ljava/lang/String;)V\n"
        "\n"
        "    invoke-virtual {v0, v1}, Landroidx/activity/C;->o(Landroid/window/OnBackInvokedDispatcher;)V"
    )

    new = (
        "    iget-object v0, p0, Landroidx/activity/q;->onBackPressedDispatcher:Landroidx/activity/C;\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v1, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v2, 0x21\n"
        "\n"
        "    if-lt v1, v2, :api33_skip_q\n"
        "\n"
        "    invoke-virtual {p0}, Landroid/app/Dialog;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object v1\n"
        "\n"
        "    const-string v2, \"onBackInvokedDispatcher\"\n"
        "\n"
        "    invoke-static {v1, v2}, Lkotlin/jvm/internal/Intrinsics;->checkNotNullExpressionValue(Ljava/lang/Object;Ljava/lang/String;)V\n"
        "\n"
        "    invoke-virtual {v0, v1}, Landroidx/activity/C;->o(Landroid/window/OnBackInvokedDispatcher;)V\n"
        "\n"
        "    :api33_skip_q\n"
        "    # --- end guard ---"
    )

    content = read(path)
    if old not in content:
        print(f"    [q.onCreate] SKIP — exact match not found (already patched?)")
        return 0
    content = content.replace(old, new)
    write(path, content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 6: Braze DefaultInAppMessageViewWrapper.smali
#   Two places calling Activity.getOnBackInvokedDispatcher() directly.
#
#   Site A (~line 1539): unregister callback during dismiss
#   Site B (~line 2386): register callback during open
# ─────────────────────────────────────────────────────────────────────────────
def patch_braze_wrapper(decoded: str) -> int:
    path = os.path.join(
        decoded,
        "smali_classes2/com/braze/ui/inappmessage/DefaultInAppMessageViewWrapper.smali",
    )
    if not os.path.isfile(path):
        print(f"    [Braze wrapper] SKIP — file not found")
        return 0

    content = read(path)
    count = 0

    # ── Site A: unregister during dismiss ──
    old_a = (
        "    if-eqz v0, :cond_1\n"
        "\n"
        "    invoke-virtual {v0}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object v0\n"
        "\n"
        "    if-eqz v0, :cond_1\n"
        "\n"
        "    invoke-interface {v0, v9}, Landroid/window/OnBackInvokedDispatcher;->unregisterOnBackInvokedCallback(Landroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    :cond_1"
    )

    new_a = (
        "    if-eqz v0, :cond_1\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v1, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v2, 0x21\n"
        "\n"
        "    if-lt v1, v2, :cond_1\n"
        "    # --- end guard ---\n"
        "\n"
        "    invoke-virtual {v0}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object v0\n"
        "\n"
        "    if-eqz v0, :cond_1\n"
        "\n"
        "    invoke-interface {v0, v9}, Landroid/window/OnBackInvokedDispatcher;->unregisterOnBackInvokedCallback(Landroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    :cond_1"
    )

    if old_a in content:
        content = content.replace(old_a, new_a)
        count += 1
    else:
        print(f"    [Braze site A] SKIP — exact match not found")

    # ── Site B: register during open ──
    old_b = (
        "    if-eqz v0, :cond_2\n"
        "\n"
        "    new-instance v0, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1;\n"
        "\n"
        "    invoke-direct {v0, p1}, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1;-><init>(Landroid/app/Activity;)V\n"
        "\n"
        "    invoke-virtual {p1}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object p1\n"
        "\n"
        "    const v1, 0xf4240\n"
        "\n"
        "    invoke-interface {p1, v1, v0}, Landroid/window/OnBackInvokedDispatcher;->registerOnBackInvokedCallback(ILandroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    invoke-virtual {p0, v0}, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper;->setOnBackInvokedCallback(Landroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    :cond_2"
    )

    new_b = (
        "    if-eqz v0, :cond_2\n"
        "\n"
        "    # --- API 33 guard (patched) ---\n"
        "    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v1, 0x21\n"
        "\n"
        "    if-lt v0, v1, :cond_2\n"
        "    # --- end guard ---\n"
        "\n"
        "    new-instance v0, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1;\n"
        "\n"
        "    invoke-direct {v0, p1}, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1;-><init>(Landroid/app/Activity;)V\n"
        "\n"
        "    invoke-virtual {p1}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object p1\n"
        "\n"
        "    const v1, 0xf4240\n"
        "\n"
        "    invoke-interface {p1, v1, v0}, Landroid/window/OnBackInvokedDispatcher;->registerOnBackInvokedCallback(ILandroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    invoke-virtual {p0, v0}, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper;->setOnBackInvokedCallback(Landroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    :cond_2"
    )

    if old_b in content:
        content = content.replace(old_b, new_b)
        count += 1
    else:
        print(f"    [Braze site B] SKIP — exact match not found")

    write(path, content)
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Patch 7: Braze dismiss callback inner class
#   DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1.smali
#   Calls Activity.getOnBackInvokedDispatcher() then unregister.
#   Skip on API < 33.
# ─────────────────────────────────────────────────────────────────────────────
def patch_braze_callback(decoded: str) -> int:
    path = os.path.join(
        decoded,
        "smali_classes2/com/braze/ui/inappmessage/"
        "DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1.smali",
    )
    if not os.path.isfile(path):
        print(f"    [Braze callback] SKIP — file not found")
        return 0

    old = (
        "    iget-object v0, p0, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1;->$it:Landroid/app/Activity;\n"
        "\n"
        "    invoke-virtual {v0}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object v0\n"
        "\n"
        "    invoke-interface {v0, p0}, Landroid/window/OnBackInvokedDispatcher;->unregisterOnBackInvokedCallback(Landroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    return-void"
    )

    new = (
        "    # --- API 33 guard (patched) ---\n"
        "    sget v0, Landroid/os/Build$VERSION;->SDK_INT:I\n"
        "\n"
        "    const/16 v1, 0x21\n"
        "\n"
        "    if-lt v0, v1, :api33_skip_braze_cb\n"
        "    # --- end guard ---\n"
        "\n"
        "    iget-object v0, p0, Lcom/braze/ui/inappmessage/DefaultInAppMessageViewWrapper$open$4$dismissInAppMessageCallback$1;->$it:Landroid/app/Activity;\n"
        "\n"
        "    invoke-virtual {v0}, Landroid/app/Activity;->getOnBackInvokedDispatcher()Landroid/window/OnBackInvokedDispatcher;\n"
        "\n"
        "    move-result-object v0\n"
        "\n"
        "    invoke-interface {v0, p0}, Landroid/window/OnBackInvokedDispatcher;->unregisterOnBackInvokedCallback(Landroid/window/OnBackInvokedCallback;)V\n"
        "\n"
        "    :api33_skip_braze_cb\n"
        "\n"
        "    return-void"
    )

    content = read(path)
    if old not in content:
        print(f"    [Braze callback] SKIP — exact match not found (already patched?)")
        return 0
    content = content.replace(old, new)
    write(path, content)
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# Patch 8 helper: guard Bundle.getSerializable(String, Class) (API 33 only)
# ─────────────────────────────────────────────────────────────────────────────
def patch_accessibility_actions(decoded: str) -> int:
    """Guard static initialiser field reads of
    AccessibilityNodeInfo$AccessibilityAction ACTION_DRAG_START,
    ACTION_DRAG_DROP and ACTION_DRAG_CANCEL which were added after API 31.
    On older platforms we replace the read with null using an
    SDK_INT check.  This prevents NoSuchFieldError crashes when
    the framework class lacks the field.
    """
    count = 0
    label_id = 0
    smali_dirs = []
    for entry in os.listdir(decoded):
        full = os.path.join(decoded, entry)
        if os.path.isdir(full) and entry.startswith("smali"):
            smali_dirs.append(full)

    for smali_dir in smali_dirs:
        for root, _, files in os.walk(smali_dir):
            for fname in files:
                if not fname.endswith(".smali"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = read(fpath)
                except Exception:
                    continue

                original = content

                # helper that inserts a version guard around a field load
                def make_guard(field_name: str, match: re.Match) -> str:
                    nonlocal label_id
                    reg = match.group(1)  # e.g. v10
                    # reuse the same register for both the SDK check and the
                    # eventual action object.  Use the next register number as a
                    # temporary for the threshold value; it typically gets
                    # overwritten later so the choice is safe.
                    reg_num = int(reg[1:])
                    thresh = f"v{reg_num + 1}"
                    lbl_ok = f":api33_ok_{field_name}_{label_id}"
                    lbl_after = f":api33_after_{field_name}_{label_id}"
                    label_id += 1
                    return (
                        f"    # --- API 33 guard for {field_name} ---\n"
                        f"    sget {reg}, Landroid/os/Build$VERSION;->SDK_INT:I\n"
                        f"    const/16 {thresh}, 0x21\n"
                        f"    if-ge {reg}, {thresh}, {lbl_ok}\n"
                        f"    const/4 {reg}, 0x0\n"
                        f"    goto {lbl_after}\n"
                        f"    {lbl_ok}\n"
                        f"    sget-object {reg}, Landroid/view/accessibility/AccessibilityNodeInfo$AccessibilityAction;->{field_name}:Landroid/view/accessibility/AccessibilityNodeInfo$AccessibilityAction;  # patched\n"
                        f"    {lbl_after}"
                    )

                # patch ACTION_DRAG_START (skip lines already marked patched)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_DRAG_START:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_DRAG_START", m),
                    content,
                )

                # patch ACTION_DRAG_DROP (same treatment)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_DRAG_DROP:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_DRAG_DROP", m),
                    content,
                )

                # patch ACTION_DRAG_CANCEL (same treatment; missing guard caused crash on API 31)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_DRAG_CANCEL:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_DRAG_CANCEL", m),
                    content,
                )

                # patch ACTION_SHOW_TEXT_SUGGESTIONS (API 32+)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SHOW_TEXT_SUGGESTIONS:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SHOW_TEXT_SUGGESTIONS", m),
                    content,
                )

                # patch ACTION_SCROLL_IN_DIRECTION (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SCROLL_IN_DIRECTION:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SCROLL_IN_DIRECTION", m),
                    content,
                )

                # patch ACTION_SHOW_ON_SCREEN (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SHOW_ON_SCREEN:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SHOW_ON_SCREEN", m),
                    content,
                )

                # patch ACTION_SCROLL_TO_POSITION (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SCROLL_TO_POSITION:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SCROLL_TO_POSITION", m),
                    content,
                )

                # patch ACTION_SCROLL_UP (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SCROLL_UP:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SCROLL_UP", m),
                    content,
                )

                # patch ACTION_SCROLL_LEFT (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SCROLL_LEFT:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SCROLL_LEFT", m),
                    content,
                )

                # patch ACTION_SCROLL_DOWN (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SCROLL_DOWN:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SCROLL_DOWN", m),
                    content,
                )

                # patch ACTION_SCROLL_RIGHT (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_SCROLL_RIGHT:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_SCROLL_RIGHT", m),
                    content,
                )

                # patch ACTION_PAGE_UP (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_PAGE_UP:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_PAGE_UP", m),
                    content,
                )

                # patch ACTION_PAGE_DOWN (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_PAGE_DOWN:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_PAGE_DOWN", m),
                    content,
                )

                # patch ACTION_PAGE_LEFT (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_PAGE_LEFT:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_PAGE_LEFT", m),
                    content,
                )

                # patch ACTION_PAGE_RIGHT (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_PAGE_RIGHT:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_PAGE_RIGHT", m),
                    content,
                )

                # patch ACTION_MOVE_WINDOW (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_MOVE_WINDOW:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_MOVE_WINDOW", m),
                    content,
                )

                # patch ACTION_IME_ENTER (API 34)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_IME_ENTER:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_IME_ENTER", m),
                    content,
                )

                # patch ACTION_PRESS_AND_HOLD (API 33)
                content = re.sub(
                    r'sget-object (v\d+), Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;->ACTION_PRESS_AND_HOLD:Landroid/view/accessibility/AccessibilityNodeInfo\$AccessibilityAction;(?!.*# patched)',
                    lambda m: make_guard("ACTION_PRESS_AND_HOLD", m),
                    content,
                )

                if content != original:
                    write(fpath, content)
                    count += 1
    return count


def patch_getserializable(decoded: str) -> int:
    """Insert SDK_INT guards around every invocation of
    Bundle.getSerializable(String, Class) which was added in API 33.
    For API < 33 the call returns null instead of crashing.
    """
    count = 0
    label_id = 0
    smali_dirs = []
    for entry in os.listdir(decoded):
        full = os.path.join(decoded, entry)
        if os.path.isdir(full) and entry.startswith("smali"):
            smali_dirs.append(full)

    for smali_dir in smali_dirs:
        for root, _, files in os.walk(smali_dir):
            for fname in files:
                if not fname.endswith(".smali"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = read(fpath)
                except Exception:
                    continue

                if "getSerializable(Ljava/lang/String;Ljava/lang/Class;)" not in content:
                    continue

                original = content
                lines = content.split("\n")
                new_lines: list[str] = []
                in_method = False
                locals_idx = None
                locals_val = 0
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if line.startswith(".method "):
                        in_method = True
                        locals_idx = None
                        locals_val = 0
                    if in_method and line.strip().startswith(".locals "):
                        locals_idx = len(new_lines)
                        try:
                            locals_val = int(line.strip().split()[1])
                        except ValueError:
                            locals_val = 0
                    # look ahead for invocation
                    m = re.match(r"(\s*)invoke-virtual \{([^}]+)\}, Landroid/os/Bundle;->getSerializable\(Ljava/lang/String;Ljava/lang/Class;\)Ljava/io/Serializable;", line)
                    if m:
                        # don't double-patch if a guard comment already appears in a few lines before
                        start_check = max(0, i - 5)
                        already = any("# --- API 33 guard (patched) ---" in lines[k] for k in range(start_check, i))
                        if already:
                            new_lines.append(line)
                            i += 1
                            continue

                        indent = m.group(1)
                        regs = [r.strip() for r in m.group(2).split(",")]
                        # find move-result line
                        result_reg = None
                        for j in range(i + 1, min(i + 3, len(lines))):
                            m2 = re.match(r"\s*move-result(?:-object)? (\w+)", lines[j])
                            if m2:
                                result_reg = m2.group(1)
                                break
                        if not result_reg:
                            new_lines.append(line)
                            i += 1
                            continue
                        # bump locals if we haven't already
                        if locals_idx is not None and locals_val is not None:
                            new_locals = locals_val + 2
                            if new_locals != locals_val:
                                # update the line in new_lines
                                new_lines[locals_idx] = f"    .locals {new_locals}"
                            guard_v1 = locals_val
                            guard_v2 = locals_val + 1
                        else:
                            guard_v1 = 0
                            guard_v2 = 1
                        label_id += 1
                        ok_label = f":api33_ok_getser_{label_id}"
                        end_label = f":api33_end_getser_{label_id}"
                        # insert guard block
                        new_lines.append(f"{indent}# --- API 33 guard (patched) ---")
                        new_lines.append(f"{indent}sget v{guard_v1}, Landroid/os/Build$VERSION;->SDK_INT:I")
                        new_lines.append(f"{indent}const/16 v{guard_v2}, 0x21")
                        new_lines.append(f"{indent}if-ge v{guard_v1}, v{guard_v2}, {ok_label}")
                        # fallback invocation on older APIs
                        bundle_reg = regs[0]
                        key_reg = regs[1] if len(regs) > 1 else regs[0]
                        new_lines.append(f"{indent}# fallback for API < 33")
                        new_lines.append(f"{indent}invoke-virtual {{{bundle_reg}, {key_reg}}}, Landroid/os/Bundle;->getSerializable(Ljava/lang/String;)Ljava/io/Serializable;")
                        new_lines.append(f"{indent}move-result-object {result_reg}")
                        new_lines.append(f"{indent}goto {end_label}")
                        new_lines.append(f"{indent}{ok_label}")
                        new_lines.append(line)
                        # also copy following move-result-object line
                        if j < len(lines):
                            new_lines.append(lines[j])
                            i = j  # skip ahead
                        new_lines.append(f"{indent}{end_label}")
                        count += 1
                        i += 1
                        continue
                    new_lines.append(line)
                    if line.startswith(".end method"):
                        in_method = False
                    i += 1

                content = "\n".join(new_lines)
                if content != original:
                    write(fpath, content)
                # we treat each file with any changes as one patch
                if content != original:
                    count += 1
    return count

# ─────────────────────────────────────────────────────────────────────────────
# Sanity check: scan for any remaining unguarded getOnBackInvokedDispatcher
# calls — i.e., the API call appears in a method that has no SDK_INT check.
# ─────────────────────────────────────────────────────────────────────────────
def sanity_check(decoded: str) -> int:
    """
    Walk all smali files. For each method body that contains
    'getOnBackInvokedDispatcher', verify it also contains 'SDK_INT'.
    Returns the number of unguarded sites found.
    """
    # we check both the onBackInvoked call and various accessibility action fields
    BAD_CALLS = [
        "getOnBackInvokedDispatcher",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_DRAG_START",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_DRAG_DROP",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SHOW_TEXT_SUGGESTIONS",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SCROLL_IN_DIRECTION",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SHOW_ON_SCREEN",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SCROLL_TO_POSITION",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SCROLL_UP",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SCROLL_LEFT",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SCROLL_DOWN",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_SCROLL_RIGHT",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_PAGE_UP",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_PAGE_DOWN",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_PAGE_LEFT",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_PAGE_RIGHT",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_MOVE_WINDOW",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_IME_ENTER",
        "AccessibilityNodeInfo$AccessibilityAction;->ACTION_PRESS_AND_HOLD",
    ]
    SDK_GUARD = "SDK_INT"
    METHOD_START = re.compile(r"^\.method ")
    METHOD_END = re.compile(r"^\.end method")

    unguarded = []

    smali_dirs = []
    for entry in os.listdir(decoded):
        full = os.path.join(decoded, entry)
        if os.path.isdir(full) and entry.startswith("smali"):
            smali_dirs.append(full)

    for smali_dir in smali_dirs:
        for root, _, files in os.walk(smali_dir):
            for fname in files:
                if not fname.endswith(".smali"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    content = read(fpath)
                except Exception:
                    continue

                # quickly skip files without any of the bad patterns
                if not any(b in content for b in BAD_CALLS):
                    continue

                # Split into method blocks and check each one
                lines = content.splitlines()
                in_method = False
                method_lines: list[str] = []
                method_name = ""
                for line in lines:
                    if METHOD_START.match(line):
                        in_method = True
                        method_lines = [line]
                        method_name = line.strip()
                    elif METHOD_END.match(line) and in_method:
                        method_lines.append(line)
                        body = "\n".join(method_lines)
                        # if any of the bad calls appear without a version guard,
                        # record the method for manual review
                        if any(b in body for b in BAD_CALLS) and SDK_GUARD not in body:
                            rel = os.path.relpath(fpath, decoded)
                            unguarded.append(f"{rel}: {method_name}")
                        in_method = False
                        method_lines = []
                    elif in_method:
                        method_lines.append(line)

    return unguarded


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <decoded_dir>")
        sys.exit(1)

    decoded = sys.argv[1]
    if not os.path.isdir(decoded):
        print(f"ERROR: Directory not found: {decoded}")
        sys.exit(1)

    print("==> Patching smali for OnBackInvokedDispatcher (API 33) compatibility...")

    total = 0
    
    # ── Patch 0b: Remove problematic interface implementations (FIRST) ───────
    n = patch_remove_interfaces(decoded)
    total += n
    print(patch_count_msg("remove interfaces", n))
    
    # ── Patches 1-7: Add SDK_INT guards ──────────────────────────────────────
    total += patch_h_dollar_l(decoded)
    print(patch_count_msg("h$l.a", total))

    n = patch_h_method_N(decoded)
    total += n
    print(patch_count_msg("h.N", n))

    n = patch_h_method_e1(decoded)
    total += n
    print(patch_count_msg("h.e1", n))

    n = patch_j_dollar_b(decoded)
    total += n
    print(patch_count_msg("j$b.a", n))

    n = patch_j_method_n(decoded)
    total += n
    print(patch_count_msg("j.n", n))

    n = patch_q_oncreate(decoded)
    total += n
    print(patch_count_msg("q.onCreate", n))

    n = patch_braze_wrapper(decoded)
    total += n
    print(patch_count_msg("Braze wrapper", n))

    n = patch_braze_callback(decoded)
    total += n
    print(patch_count_msg("Braze callback", n))

    # ── NEW Patch: guard accessibility ACTION_DRAG_START/DRAG_DROP
    n = patch_accessibility_actions(decoded)
    total += n
    print(patch_count_msg("accessibility actions", n))

    # ── Patch 8: API 33-only Bundle.getSerializable with Class arg
    n = patch_getserializable(decoded)
    total += n
    print(patch_count_msg("getSerializable guard", n))

    # ── Patch 0: Global type replacement (AFTER specific patches) ────────────
    n = patch_field_types(decoded)
    total += n
    print(patch_count_msg("field types", n))

    print(f"\n    Total: {total} patch(es) applied across all files.")

    # ── Sanity check ──────────────────────────────────────────────────────────
    print("\n==> Sanity check: scanning for unguarded getOnBackInvokedDispatcher calls...")
    unguarded = sanity_check(decoded)
    if unguarded:
        print(f"    [FAIL] {len(unguarded)} unguarded call(s) remain — manual review needed:")
        for site in unguarded:
            print(f"      - {site}")
        sys.exit(1)
    else:
        print("    [OK] All getOnBackInvokedDispatcher calls are guarded by SDK_INT checks.")


if __name__ == "__main__":
    main()
