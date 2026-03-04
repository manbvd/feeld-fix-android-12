#!/usr/bin/env python3
"""
fix_manifest.py
Fixes malformed meta-data tags in AndroidManifest.xml
"""
import xml.etree.ElementTree as ET
import sys
import os


def fix_manifest(manifest_file):
    """Fix meta-data tags that lack both android:value and android:resource"""
    if not os.path.isfile(manifest_file):
        print(f"ERROR: Manifest file not found: {manifest_file}", file=sys.stderr)
        return False

    try:
        tree = ET.parse(manifest_file)
        root = tree.getroot()

        ANDROID_NS = '{http://schemas.android.com/apk/res/android}'

        fixed = False
        # Find all meta-data elements
        for elem in root.iter():
            if 'meta-data' not in elem.tag:
                continue

            name = next(
                (elem.attrib[k] for k in elem.attrib if k.endswith('name')),
                'unknown',
            )

            # Check for both value and resource attributes (namespace-aware)
            has_value = any(k.endswith('value') for k in elem.attrib.keys())
            has_resource = any(
                k.endswith('resource') for k in elem.attrib.keys()
            )

            # Fix 1: meta-data with neither value nor resource
            if not has_value and not has_resource:
                print(f"Fixing {name}: adding android:value (was missing)")
                elem.set(f'{ANDROID_NS}value', '')
                fixed = True

            # Fix 2: resource="@null" — Android 12 rejects this
            res_key = next(
                (k for k in elem.attrib if k.endswith('resource')), None
            )
            if res_key and elem.attrib[res_key] == '@null':
                print(f"Fixing {name}: replacing @null resource with value=\"\"")
                del elem.attrib[res_key]
                elem.set(f'{ANDROID_NS}value', '')
                fixed = True

        if fixed:
            tree.write(manifest_file, encoding='utf-8', xml_declaration=True)
            print("Manifest fixed")
            return True

        print("No manifest fixes needed")
        return True

    except Exception as e:
        print(f"ERROR: Failed to fix manifest: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <manifest_file>", file=sys.stderr)
        sys.exit(1)

    manifest_path = sys.argv[1]
    success = fix_manifest(manifest_path)
    sys.exit(0 if success else 1)
