#!/usr/bin/env python3
import os

DRAWABLE_DIR = "work/base_decoded/res/drawable-anydpi-v21"
ICONS = [
    "exo_icon_pause",
    "exo_icon_play",
    "exo_icon_next",
    "exo_icon_previous",
    "exo_icon_rewind",
    "exo_icon_fastforward",
    "exo_icon_fullscreen_enter",
    "exo_icon_fullscreen_exit",
    "exo_icon_shuffle_on",
    "exo_icon_shuffle_off",
    "exo_icon_repeat_one",
    "exo_icon_repeat_off",
    "exo_icon_repeat_all",
    "exo_icon_stop",
    "exo_ic_audiotrack",
    "exo_ic_check",
    "exo_ic_speed",
    "exo_ic_subtitle_on",
    "exo_ic_subtitle_off",
    "exo_ic_settings"
]

TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
  <path
      android:fillColor="#FF000000"
      android:pathData="M12,2C6.48,2 2,6.48 2,12s4.48,10 10,10 10,-4.48 10,-10S17.52,2 12,2zM12,20c-4.41,0 -8,-3.59 -8,-8s3.59,-8 8,-8 8,3.59 8,8 -3.59,8 -8,8z"/>
</vector>
"""

def create_dummies():
    if not os.path.exists(DRAWABLE_DIR):
        os.makedirs(DRAWABLE_DIR)

    for icon in ICONS:
        path = os.path.join(DRAWABLE_DIR, f"{icon}.xml")
        with open(path, 'w') as f:
            f.write(TEMPLATE)
        print(f"Created dummy {icon}.xml")

if __name__ == "__main__":
    create_dummies()
