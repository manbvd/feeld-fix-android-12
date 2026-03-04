#!/usr/bin/env python3
import os
import sys
import re

def fix_flags(decoded_dir):
    print(f"Scanning {decoded_dir} for API 33 Flags usage...")
    
    # Flags types to look for
    flag_types = [
        "PackageInfoFlags",
        "ApplicationInfoFlags",
        "ResolveInfoFlags",
        "ComponentInfoFlags"
    ]
    
    # Method signatures to update
    # Map from (MethodName, FlagType) to (NewSignature)
    # Actually, we can just replace the FlagType in the signature with 'I'
    
    files_patched = 0
    
    for root, dirs, files in os.walk(decoded_dir):
        for fname in files:
            if not fname.endswith(".smali"):
                continue
            
            fpath = os.path.join(root, fname)
            with open(fpath, 'r') as f:
                content = f.read()
            
            original_content = content
            lines = content.splitlines()
            new_lines = []
            
            i = 0
            while i < len(lines):
                line = lines[i]
                
                # Check for .of(J) call with loose whitespace
                # invoke-static {v1, v2}, Landroid/content/pm/PackageManager$PackageInfoFlags;->of(J)Landroid/content/pm/PackageManager$PackageInfoFlags;
                match_of = re.search(r'invoke-static\s*\{\s*([vp]\d+)\s*,\s*([vp]\d+)\s*\}\s*,\s*Landroid/content/pm/PackageManager\$(\w+)Flags;->of\(J\)Landroid/content/pm/PackageManager\$\3Flags;', line)
                
                if match_of:
                    reg_low = match_of.group(1)
                    reg_high = match_of.group(2)
                    flag_type = match_of.group(3)
                    
                    # Look ahead for move-result-object, skipping empty lines/comments
                    j = i + 1
                    found_move = False
                    while j < len(lines):
                        next_line = lines[j].strip()
                        if not next_line or next_line.startswith('.') or next_line.startswith('#'):
                            j += 1
                            continue
                        
                        match_move = re.search(r'move-result-object\s+([vp]\d+)', next_line)
                        if match_move:
                            result_reg = match_move.group(1)
                            # Replace the invoke-static line with long-to-int
                            # We replace the original line with the conversion
                            new_lines.append(f"    long-to-int {result_reg}, {reg_low}")
                            
                            # We also need to consume the lines we skipped over + the move-result-object line
                            # But we should keep the blank lines/comments if possible? 
                            # Actually, it's safer to just skip the move-result-object line and append intermediate lines?
                            # To keep it simple: 
                            # 1. Append `long-to-int` (this replaces `invoke-static`)
                            # 2. Add back the intermediate empty lines
                            # 3. Skip the `move-result-object` line (don't add it)
                            
                            # Correction: My previous logic was replacing lines in `new_lines`.
                            # Here I'm iterating `lines` and appending to `new_lines`.
                            
                            # Add intermediate lines
                            for k in range(i + 1, j):
                                new_lines.append(lines[k])
                                
                            # Advance main loop index `i` to `j + 1` (skipping move-result)
                            i = j + 1
                            found_move = True
                        break
                    
                    if found_move:
                        continue
                    else:
                        print(f"WARN: Found .of(J) without immediate move-result-object in {fpath}:{i+1}")
                        new_lines.append(line)
                        i += 1
                        continue

                # Check for method calls usage using the Flags types
                # ... existing check logic ...
                # Regex to match Landroid/content/pm/PackageManager$*Flags;
                if 'Landroid/content/pm/PackageManager$' in line and 'Flags;' in line:
                    # Check if it is one of our target flags
                    patched_line = line
                    for ft in flag_types:
                        target = f"Landroid/content/pm/PackageManager${ft};"
                        if target in patched_line:
                            # Replace with I
                            patched_line = patched_line.replace(target, "I")
                    
                    if patched_line != line:
                        new_lines.append(patched_line)
                        i += 1
                        continue

                new_lines.append(line)
                i += 1
            
            new_content = "\n".join(new_lines)
            if new_content != original_content:
                with open(fpath, 'w') as f:
                    f.write(new_content)
                files_patched += 1
                print(f"Patched {fpath}")

    print(f"Total files patched: {files_patched}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        fix_flags(sys.argv[1])
    else:
        fix_flags("work/base_decoded")
