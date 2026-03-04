#!/usr/bin/env python3
import os

TARGET_FILE = "work/base_decoded/res/drawable/abc_edit_text_material.xml"

# Standard Material EditText background shape approximation
NEW_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<inset xmlns:android="http://schemas.android.com/apk/res/android"
       android:insetLeft="4dp"
       android:insetTop="4dp"
       android:insetRight="4dp"
       android:insetBottom="4dp">
    <selector>
        <item android:state_enabled="false">
            <shape android:shape="rectangle">
                <solid android:color="#00000000"/>
                <stroke android:width="1dp" android:color="?attr/colorControlNormal" android:alpha="?android:attr/disabledAlpha"/>
                <corners android:radius="4dp"/>
            </shape>
        </item>
        <item android:state_pressed="false" android:state_focused="false">
             <shape android:shape="rectangle">
                <solid android:color="#00000000"/>
                <stroke android:width="1dp" android:color="?attr/colorControlNormal"/>
                <corners android:radius="4dp"/>
            </shape>
        </item>
        <item>
             <shape android:shape="rectangle">
                <solid android:color="#00000000"/>
                <stroke android:width="2dp" android:color="?attr/colorControlActivated"/>
                <corners android:radius="4dp"/>
            </shape>
        </item>
    </selector>
</inset>
"""

def fix_edittext_crash():
    if not os.path.exists(TARGET_FILE):
        print(f"File not found: {TARGET_FILE}. Maybe base APK not decoded yet?")
        # We don't exit error because this might run before decode in some pipelines, 
        # but in our pipeline it runs after.
        return

    with open(TARGET_FILE, 'w') as f:
        f.write(NEW_CONTENT)
    print(f"Patched {TARGET_FILE} with safe shape drawable.")

if __name__ == "__main__":
    fix_edittext_crash()
