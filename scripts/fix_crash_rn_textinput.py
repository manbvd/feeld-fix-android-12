#!/usr/bin/env python3
import os

target_file = "work/base_decoded/res/drawable/rn_edit_text_material.xml"

if not os.path.exists(target_file):
    print(f"File not found: {target_file}")
    # It might be in a different folder if not found, but we know it's there from previous checks
else:
    new_content = """<?xml version="1.0" encoding="utf-8"?>
<inset xmlns:android="http://schemas.android.com/apk/res/android"
    android:insetLeft="@dimen/abc_edit_text_inset_horizontal_material"
    android:insetRight="@dimen/abc_edit_text_inset_horizontal_material"
    android:insetTop="@dimen/abc_edit_text_inset_top_material"
    android:insetBottom="@dimen/abc_edit_text_inset_bottom_material">
    <selector>
        <item android:state_enabled="false">
            <shape android:shape="rectangle">
                <solid android:color="@android:color/transparent"/>
            </shape>
        </item>
        <item>
            <shape android:shape="rectangle">
                <solid android:color="@android:color/transparent"/>
            </shape>
        </item>
    </selector>
</inset>
"""
    with open(target_file, "w") as f:
        f.write(new_content)
    print(f"Patched {target_file}")
