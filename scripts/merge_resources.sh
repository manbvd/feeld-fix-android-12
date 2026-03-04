#!/usr/bin/env bash
set -euo pipefail

# Decompile base if not already (assuming 02_patch.sh did it)
# We assume work/base_decoded exists.

echo "Merging split resources..."

# List of splits to merge
SPLITS=("split_config.xxhdpi.apk" "split_config.xhdpi.apk" "split_config.hdpi.apk" "split_config.arm64_v8a.apk" "split_config.armeabi_v7a.apk")

mkdir -p work/temp_merge

for split in "${SPLITS[@]}"; do
    if [[ -f "work/extracted/$split" ]]; then
        echo "Processing $split..."
        unzip -q -o "work/extracted/$split" -d "work/temp_merge/$split"
        
        # Copy Assets
        if [[ -d "work/temp_merge/$split/assets" ]]; then
            cp -r "work/temp_merge/$split/assets/"* "work/base_decoded/assets/" 2>/dev/null || true
        fi
        
        # Copy Libs
        if [[ -d "work/temp_merge/$split/lib" ]]; then
            cp -r "work/temp_merge/$split/lib/"* "work/base_decoded/lib/" 2>/dev/null || true
        fi
        
        # Copy Drawables (and other res, excluding values)
        if [[ -d "work/temp_merge/$split/res" ]]; then
            # We iterate to avoid overwriting values XMLs recklessly, but for density splits it's usually fine
            # We skip values* to avoid XML conflicts for now, unless needed.
            # But wait, we NEED drawable-anydpi-v21 from xxhdpi split!
            
            # Copy all res folders except values*
            find "work/temp_merge/$split/res" -mindepth 1 -maxdepth 1 -type d -not -name "values*" | while read -r dir; do
                dirname=$(basename "$dir")
                mkdir -p "work/base_decoded/res/$dirname"
                # Only copy non-XML files (PNG, JPG, etc) from drawables to avoid binary XML issues
                # But copy everything from non-drawable folders (like layout? no layout is also xml)
                
                if [[ "$dirname" == "drawable"* ]]; then
                     # Copy only images, AND strictly filter for exo_ or com_braze_ or similar app-specific assets
                     # to avoid copying compiled 9-patch files from support libs that break aapt2
                     find "$dir" -maxdepth 1 -type f \( -name "exo_*.png" -o -name "com_braze_*.png" -o -name "vrff_*.png" -o -name "ic_*.png" \) | while read -r img; do
                        # Check if it is a 9-patch
                        if [[ "$img" == *".9.png" ]]; then
                             echo "Skipping 9-patch: $img"
                             continue
                        fi
                        cp "$img" "work/base_decoded/res/$dirname/"
                     done
                else
                     # For other folders (color, anim, etc), they are likely XML too and will cause issues if binary.
                     # We should probably skip them too unless we can decompile them.
                     # For now, let's assume we only need the images from drawables.
                     echo "Skipping potential binary XMLs in $dirname"
                fi
            done
        fi
    fi
done

rm -rf work/temp_merge
echo "Merge complete."
