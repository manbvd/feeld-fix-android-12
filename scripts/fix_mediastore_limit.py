import os
import re

def fix_mediastore_limit(smali_dir):
    pattern = re.compile(r'invoke-static {}, Landroid/provider/MediaStore;->getPickImagesMaxLimit\(\)I\s+move-result ([vp]\d+)')
    
    for root, dirs, files in os.walk(smali_dir):
        for file in files:
            if file.endswith(".smali"):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                if 'getPickImagesMaxLimit' in content:
                    print(f"Patching {filepath}")
                    # Replace invoke + move-result with const/16
                    # We use a lambda to capture the register name from the match
                    new_content = pattern.sub(lambda m: f"const/16 {m.group(1)}, 0x64", content)
                    
                    if content != new_content:
                        with open(filepath, 'w') as f:
                            f.write(new_content)
                        print(f"Patched {filepath}")
                    else:
                        print(f"Could not match pattern in {filepath}")

if __name__ == "__main__":
    fix_mediastore_limit("work/base_decoded")
