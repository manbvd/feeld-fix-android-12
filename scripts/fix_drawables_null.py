#!/usr/bin/env python3
import os

RES_DIR = "work/base_decoded/res"

def fix_all_null_drawables():
    print(f"Scanning {RES_DIR} for invalid android:drawable=\"@null\"...")
    count = 0
    
    for root, dirs, files in os.walk(RES_DIR):
        if "drawable" in os.path.basename(root):
            for file in files:
                if file.endswith(".xml"):
                    file_path = os.path.join(root, file)
                    with open(file_path, 'r') as f:
                        content = f.read()
                    
                    if 'android:drawable="@null"' in content:
                        # Replace @null with @android:color/transparent
                        new_content = content.replace('android:drawable="@null"', 'android:drawable="@android:color/transparent"')
                        
                        with open(file_path, 'w') as f:
                            f.write(new_content)
                        
                        print(f"Fixed: {file_path}")
                        count += 1

    print(f"Total files fixed: {count}")

if __name__ == "__main__":
    if not os.path.exists(RES_DIR):
        print(f"Directory not found: {RES_DIR}. Ensure the APK is decoded.")
    else:
        fix_all_null_drawables()
