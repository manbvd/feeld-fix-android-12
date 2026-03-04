import os
import shutil
import re

base_decoded = "work/base_decoded"
res_xml = os.path.join(base_decoded, "res", "xml")
os.makedirs(res_xml, exist_ok=True)

config_path = os.path.join(res_xml, "network_security_config.xml")
if not os.path.exists(config_path):
    with open(config_path, "w") as f:
        f.write('''<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
''')
    print(f"Created {config_path}")
else:
    print(f"File {config_path} already exists")

manifest_path = os.path.join(base_decoded, "AndroidManifest.xml")
if os.path.exists(manifest_path):
    with open(manifest_path, "r") as f:
        manifest_content = f.read()

    if 'networkSecurityConfig' not in manifest_content:
        print("Injecting networkSecurityConfig into AndroidManifest.xml")
        # Match <application followed by whitespace
        # We want to insert it right after <application
        # The namespace prefix might be different, but looking at the file, it is ns0.
        # However, to be robust, we could just inject it with the same prefix used for other attributes if possible.
        # But for now, since we saw ns0 in the file, we will use ns0.
        # If we want to be safer, we could parse the root element to find the prefix for "http://schemas.android.com/apk/res/android".
        # But let's stick to simple text replacement for now assuming ns0 as seen in the file.
        
        # We also need to be careful if <application> spans multiple lines or has attributes immediately.
        new_content = re.sub(r'<application\s', '<application android:networkSecurityConfig="@xml/network_security_config" ', manifest_content, count=1)
        
        if new_content != manifest_content:
            with open(manifest_path, "w") as f:
                f.write(new_content)
            print("Updated AndroidManifest.xml")
        else:
            print("Could not find <application tag to inject networkSecurityConfig")
    else:
        print("networkSecurityConfig already present in AndroidManifest.xml")
else:
    print(f"Manifest not found at {manifest_path}")
