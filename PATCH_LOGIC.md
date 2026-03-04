# Patch Logic for Android 12 Compatibility

## Problem Statement

The Feeld app (feeld.apkm) targets Android 13 (API 33) as minimum and uses API 33-specific classes:
- `android.window.OnBackInvokedCallback`
- `android.window.OnBackInvokedDispatcher`

These classes do not exist on Android 12 (API 31), causing crashes:
1. `ClassNotFoundException` when the class loader tries to resolve type references
2. `NoClassDefFoundError` when fields/methods declare these types

## Root Causes

1. **Type Resolution at Class Load Time**: When a class declares a field, method parameter, or return type using `OnBackInvoked*` types, the class loader attempts to resolve these types. If they don't exist, the entire class fails to load.

2. **Interface Implementations**: Classes implementing `OnBackInvokedCallback` (e.g., `androidx.activity.D`) cannot load if the interface doesn't exist, causing `IncompatibleClassChangeError`.

3. **Method Signatures**: Methods with `OnBackInvoked*` parameters/returns cause type resolution failures even if the method is never called.

## Patching Strategy

The approach has **three layers**:

### Layer 1: Remove Interface Declarations (Patch 0b)
**Goal**: Prevent type resolution failures for non-existent interfaces

**What it does**: Removes `.implements Landroid/window/OnBackInvoked*` declarations from all smali files

**Why**: Classes can still exist and be instantiated without declaring they implement an interface. Since all actual usages are guarded by SDK_INT checks, the missing interface contract is safe.

**Files affected**: `androidx.activity.D` and similar callback classes

### Layer 2: Add SDK_INT Guards (Patches 1-8)
**Goal**: Prevent actual calls to API 33+ methods on API 31

**What it does**: Wraps all calls to `getOnBackInvokedDispatcher()` with SDK version checks:
```smali
sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
const/16 v1, 0x21  ; 0x21 = 33 in hex
if-ge v0, v1, :skip_label
  ; actual API 33 code here
:skip_label
```

**Important**: When adding guards, ensure `.locals` in the method header has enough registers (typically increased from 1 to 2 to accommodate v0 and v1)

**Patches applied to**:
1. `h$l.smali` - static helper method
2. `h.smali` (method N) - AppCompat delegate
3. `h.smali` (method e1) - back-invoked-dispatcher management
4. `j$b.smali` - Kotlin wrapper returning dispatcher
5. `j.smali` (method n) - lifecycle callback calling `C.o()` with dispatcher (includes .locals adjustment)
6. `q.smali` - ComponentDialog.onCreate
7. Braze `DefaultInAppMessageViewWrapper.smali` (2 sites)
8. Braze callback inner class

**Order**: Must run **before** Layer 3 (type replacement) because Layer 3 changes type signatures, breaking exact text matches

### Layer 3: Replace Type Signatures (Patch 0)
**Goal**: Replace problematic type references with safe Object type

**What it does**: Globally replaces:
- Field declarations: `.field foo:Landroid/window/OnBackInvokedDispatcher;` → `.field foo:Ljava/lang/Object;`
- Field accesses: `->foo:Landroid/window/OnBackInvokedDispatcher;` → `->foo:Ljava/lang/Object;`
- Method signatures: `foo(Landroid/window/OnBackInvokedCallback;)V` → `foo(Ljava/lang/Object;)V`

**Conditions**: SKIPS `.implements`, `.annotation`, and `value =` lines to avoid breaking interface contracts

**Why**: Prevents type resolution failures on API 31. Since the methods are guarded, the type is never actually used at runtime.

**Order**: Must run **after** Layer 2 (to let SDK_INT guards match first)

### Layer 4: Feature Flags & Compat (Patch 13)
**Goal**: Disable Android 13+ specific features on older devices

**Problem**: The app checks for photo picker availability using a method `h.d$a.d()` that unconditionally returns `true`. This causes the app to call `MediaStore.getPickImagesMaxLimit()`, which only exists on API 33+, leading to a crash on Android 12.

**Fix**: Patch `work/base_decoded/smali/h/d$a.smali` method `d()` to check `SDK_INT >= 33`.

```smali
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
```

### Layer 5: Fix `findOnBackInvokedDispatcher` Lookup (Patch 14)
**Goal**: Prevent crash when calling `View.findOnBackInvokedDispatcher()` on Android 12

**Problem**: The app calls `View.findOnBackInvokedDispatcher()` (API 33+) without checks in several places:
- `androidx.appcompat.widget.Toolbar$e.a()`
- `u0.m$a.d()` and `e()` (likely `ViewCompat` helper)
- `dc.c$b.a()` and `b()`

**Fix**: `scripts/fix_crash_back_dispatcher_lookup.py` patches these methods to check `SDK_INT >= 33`. If the version is lower, it returns `null` (0x0).
- Increases `.locals` count to accommodate SDK check registers.
- Wraps the call in an SDK check block.

```smali
sget v0, Landroid/os/Build$VERSION;->SDK_INT:I
const/16 v1, 0x21
if-lt v0, v1, :cond_api33
    invoke-virtual {p0}, Landroid/view/View;->findOnBackInvokedDispatcher()Ljava/lang/Object;
    move-result-object p0
    goto :end_api33
:cond_api33
    const/4 p0, 0x0
:end_api33
```

### Layer 6: Disable Location Dialog & Mock Detection (Patch 15)
**Goal**: Improve user experience and prevent location mocking detection.

**Problem**:
1. The app forces a system dialog to enable location (`showLocationDialog: true`) on every request.
2. The app detects fake GPS applications (`Location.isFromMockProvider()`) and likely flags the user.

**Fix**:
1. **Disable Dialog**: In `work/base_decoded/smali_classes2/V4/f.smali`, force the `showLocationDialog` flag (register `v11`) to `false` (0) before the constructor call.
2. **Disable Mock Detection**: In `work/base_decoded/smali_classes2/V4/h.smali`, replace the call to `isFromMockProvider()` with `const/4 p0, 0x0` (false).

## Execution Order

```
1. patch_remove_interfaces() → Remove .implements declarations
2. patch_h_dollar_l()       → Guard Activity.getOnBackInvokedDispatcher()
3. patch_h_method_N()       → Guard AppCompat dispatcher assignment
4. patch_h_method_e1()      → Guard dispatcher management
5. patch_j_dollar_b()       → Guard Kotlin wrapper return value
6. patch_j_method_n()       → Guard lifecycle callback C.o() call
7. patch_q_oncreate()       → Guard ComponentDialog.onCreate
8. patch_braze_wrapper()    → Guard Braze wrapper (2 sites)
9. patch_braze_callback()   → Guard Braze callback
10. patch_accessibility_actions() → Guard static references to
    AccessibilityNodeInfo$AccessibilityAction fields (ACTION_DRAG_START/ACTION_DRAG_DROP/ACTION_DRAG_CANCEL)
11. patch_field_types()      → Replace all OnBackInvoked* types with Object
12. sanity_check()          → Verify all getOnBackInvokedDispatcher and
    accessibility field accesses have SDK_INT guards
```

## Known Issues & Limitations

### Issue 1: Type Replacement Side Effects
- **Problem**: Replacing `OnBackInvokedDispatcher` with `Object` in method signatures changes the contract
- **Risk**: Code expecting the specific type at runtime could fail (though it won't, because guards prevent execution on API 31)
- **Mitigation**: SDK_INT guards ensure the guarded code never runs on API 31

### Issue 2: Interface Removal Risks
- **Problem**: Removing `.implements` declarations breaks the interface contract at the class level
- **Risk**: Reflection-based code checking for interface implementations would fail
- **Mitigation**: Feeld app doesn't appear to use such checks; guards ensure callbacks are never used on API 31

### Issue 3: Samsung Knox Sandboxing
- **Problem**: Self-signed APKs get sandboxed to "work" profile
- **Cause**: Original certificate needed; we're using self-signed `patch.keystore`
- **Workaround**: App may run fine from work profile despite sandboxing (Verified: Yes it does)

### Issue 4: NullPointerException in androidx.activity.C.o()
- **Problem**: `androidx.activity.j.n()` lifecycle callback calls `C.o()` with a null dispatcher parameter on API 31
- **Cause**: `j$b.a()` returns null on API 31, but `C.o()` has `@NonNull` annotation on the dispatcher parameter
- **Solution**: Guard the `C.o()` call with SDK_INT check to skip the entire call on API < 33
- **Key Detail**: Must update `.locals 1` → `.locals 2` in the method header because the guard needs v0 and v1 registers
- **Affected**: `androidx.activity.j.smali` method `n()`

### Issue 5: Register Allocation in Smali Patches
- **Problem**: Adding SDK_INT guards requires v0 and v1 registers, but methods may declare `.locals 1` (only v0 available)
- **Solution**: When adding guards, increment `.locals` from N to N+1 to accommodate the additional registers
- **Impact**: Critical to avoid register overflow errors at runtime or assembly time
- **Example**: `.locals 1` → `.locals 2` when adding a guard that uses v0 and v1

### Issue 6: RNAppsFlyer Crash
- **Problem**: `RNAppsFlyer` crashes on startup with `NoSuchMethodError` or `RuntimeException`.
- **Cause**: Attempts to access API 33+ PackageManager flags or methods.
- **Solution**: Suppress the crash by wrapping `startSdk` in a try-catch block catching `Throwable`.
- **Affected**: `com.appsflyer.reactnative.RNAppsFlyerModule`

### Issue 7: Missing Split Resources (exo_controls_pause)
- **Problem**: App crashes with `Resources$NotFoundException` for `exo_controls_pause`.
- **Cause**: `apktool` only recompiles `base.apk`, losing resources from split APKs. Also, merged binary XMLs break `aapt2`.
- **Solution**: Merge split resources (images only), skipping binary XMLs to avoid `aapt2` errors. Generate dummy vector drawables for missing XML icons. Fix `drawables.xml` references.

### Issue 8: ProfileInstaller Crash
- **Problem**: Crash in `androidx.profileinstaller.h$a.a()` calling `PackageManager.getPackageInfo(String, PackageInfoFlags)`.
- **Cause**: `PackageInfoFlags` API was introduced in API 33. The method call is not guarded.
- **Solution**: Patch `androidx/profileinstaller/h$a.smali` to guard the call with `SDK_INT >= 33`. Use legacy `getPackageInfo(String, int)` for older versions.
- **Affected**: `androidx.profileinstaller.h$a.smali`

### Issue 9: EditText Background Crash (NinePatchDrawable)
- **Problem**: App crashes with `NullPointerException` in `NinePatchDrawable.getOpacity()` when opening screens with text inputs.
- **Cause**: `abc_edit_text_material.xml` was decompiled with `android:src="@null"` because the original 9-patch source was in a split APK and not properly merged/decoded (we skipped 9-patches to avoid build errors). This resulted in a `NinePatchDrawable` with null state.
- **Solution**: Replace `abc_edit_text_material.xml` with a safe XML selector using shape drawables (rectangle with stroke/corners) that approximates the Material Design text field look.
- **Affected**: `res/drawable/abc_edit_text_material.xml`

### Issue 10: PendingIntent Mutability Crash
- **Problem**: App crashes on API 31+ with `IllegalArgumentException: ... must be marked as FLAG_IMMUTABLE or FLAG_MUTABLE`.
- **Cause**: Android 12 requires explicit mutability flags for `PendingIntent`. Older libraries or code paths miss this flag.
- **Solution**:
    1. Patch `com.masteratul.exceptionhandler.DefaultErrorScreen` to include `FLAG_IMMUTABLE` (0x4000000) in `getActivity`.
    2. Patch `androidx.work.impl.utils.ForceStopRunnable` to inject `FLAG_IMMUTABLE` in `getBroadcast`.
- **Affected**:
    - `com.masteratul.exceptionhandler.DefaultErrorScreen.smali`
    - `androidx.work.impl.utils.ForceStopRunnable.smali`

## Testing Checklist

- [ ] App launches without ClassNotFoundException
- [ ] App launches without IncompatibleClassChangeError  
- [ ] App launches without NoClassDefFoundError
- [ ] Back button handling works (relies on OnBackInvokedDispatcher on API 33+)
- [ ] Back button handling gracefully disabled on API 31
- [ ] Sanity check passes (no unguarded API 33 calls)
- [ ] App functions normally otherwise

## Potential Improvements

1. **Use Actual Synthetic Interfaces**: Create minimal synthetic interface stubs that implement nothing, instead of removing interfaces entirely

2. **Runtime Method Patching**: Instead of static patching, inject bytecode that checks SDK_INT at method entry

3. **Conditional Dex Loading**: Use separate dex classes for API 33+ features, loaded conditionally

4. **Wrapping Strategy**: Create wrapper classes that conditionally delegate to real implementations

5. **Original Signing**: If Feeld's original signing key can be obtained, re-sign to avoid Knox sandboxing

## References

- API 33: Android 13 (Tiramisu)
- API 31: Android 12 (Snow Cone) 
- OnBackInvokedCallback introduced in API 33
- OnBackInvokedDispatcher introduced in API 33
