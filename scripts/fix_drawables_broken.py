#!/usr/bin/env python3
import os
import re

DRAWABLES_XML = "work/base_decoded/res/values/drawables.xml"
RES_DIR = "work/base_decoded/res"

def find_drawable(name):
    # Search for drawable file in any drawable-* folder
    # We look for name.xml, name.png, name.9.png
    for root, dirs, files in os.walk(RES_DIR):
        if "drawable" in os.path.basename(root):
            for f in files:
                if f.startswith(name + ".") and (f.endswith(".xml") or f.endswith(".png")):
                    return f"@drawable/{name}"
    return None

def fix_drawables():
    if not os.path.exists(DRAWABLES_XML):
        print(f"File not found: {DRAWABLES_XML}")
        return

    with open(DRAWABLES_XML, 'r') as f:
        lines = f.readlines()

    new_lines = []
    fixed_count = 0

    for line in lines:
        match = re.search(r'<drawable name="([^"]+)"\s*/>', line)
        if match:
            name = match.group(1)
            target = None

            # Heuristics
            if name.startswith("exo_controls_"):
                suffix = name.replace("exo_controls_", "")
                target = find_drawable(f"exo_icon_{suffix}")
            
            if not target and name.startswith("exo_legacy_controls_"):
                suffix = name.replace("exo_legacy_controls_", "")
                target = find_drawable(f"exo_icon_{suffix}")

            if not target and name.startswith("exo_styled_controls_"):
                suffix = name.replace("exo_styled_controls_", "")
                # Try exact suffix first
                target = find_drawable(f"exo_ic_{suffix}")
                
                # Try mappings
                if not target:
                    if suffix == "pause": 
                        target = find_drawable("exo_ic_pause_circle_filled")
                        if not target: target = find_drawable("exo_icon_pause") # Fallback to dummy
                    if suffix == "play": 
                        target = find_drawable("exo_ic_play_circle_filled")
                        if not target: target = find_drawable("exo_icon_play") # Fallback to dummy
                    if suffix == "simple_fastforward": 
                        target = find_drawable("exo_ic_forward")
                        if not target: target = find_drawable("exo_icon_fastforward")
                    if suffix == "simple_rewind": 
                        target = find_drawable("exo_ic_rewind")
                        if not target: target = find_drawable("exo_icon_rewind")
                    if suffix == "check": target = find_drawable("exo_ic_check")
                    if suffix == "settings": target = find_drawable("exo_ic_settings")
                    if suffix == "speed": target = find_drawable("exo_ic_speed")
                    if suffix == "audiotrack": target = find_drawable("exo_ic_audiotrack")
                    if suffix == "subtitle_on": target = find_drawable("exo_ic_subtitle_on")
                    if suffix == "subtitle_off": target = find_drawable("exo_ic_subtitle_off")
                    if suffix == "fullscreen_enter": 
                        target = find_drawable("exo_ic_fullscreen_enter")
                        if not target: target = find_drawable("exo_icon_fullscreen_enter")
                    if suffix == "fullscreen_exit": 
                        target = find_drawable("exo_ic_fullscreen_exit")
                        if not target: target = find_drawable("exo_icon_fullscreen_exit")
                    if suffix == "repeat_all": target = find_drawable("exo_icon_repeat_all") # fallback to icon
                    if suffix == "repeat_one": target = find_drawable("exo_icon_repeat_one")
                    if suffix == "repeat_off": target = find_drawable("exo_icon_repeat_off")
                    if suffix == "shuffle_on": target = find_drawable("exo_icon_shuffle_on")
                    if suffix == "shuffle_off": target = find_drawable("exo_icon_shuffle_off")

            if not target and name.startswith("exo_notification_"):
                 suffix = name.replace("exo_notification_", "")
                 target = find_drawable(f"exo_icon_{suffix}")
                 if not target and suffix == "small_icon":
                     target = find_drawable("exo_icon_circular_play") # Fallback

            # General fallback to transparent if still not found
            if not target:
                print(f"WARN: Could not map {name}, using transparent")
                target = "@android:color/transparent"
            
            print(f"Fixing {name} -> {target}")
            new_lines.append(f'    <item name="{name}" type="drawable">{target}</item>\n')
            fixed_count += 1
        else:
            new_lines.append(line)

    with open(DRAWABLES_XML, 'w') as f:
        f.writelines(new_lines)
    
    print(f"Fixed {fixed_count} drawables.")

if __name__ == "__main__":
    fix_drawables()
