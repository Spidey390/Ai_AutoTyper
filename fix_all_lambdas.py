import re
import os

def fix_file(filepath):
    with open(filepath, "r") as f:
        content = f.read()

    # Ai_AutoTyper_Windows/main.py format:
    # app.after(0, lambda: toast.show(f"❌ Error: {str(e)}", DANGER))
    content = re.sub(
        r'app\.after\(0,\s*lambda:\s*toast\.show\(f"❌ Error: \{str\(e\)\}", DANGER\)\)',
        r'err_str = str(e)\n            app.after(0, lambda err=err_str: toast.show(f"❌ Error: {err}", DANGER))',
        content
    )
    
    # Also handle the debug print version if it exists
    content = re.sub(
        r'err_msg = str\(e\)\n\s*app\.after\(0,\s*lambda err=err_msg:\s*toast\.show\(f"❌ Error: \{err\}", DANGER\)\)',
        r'err_msg = str(e)\n            app.after(0, lambda err=err_msg: toast.show(f"❌ Error: {err}", DANGER))',
        content
    )

    # main.py (root) format:
    # app.after(0, lambda: toast.show(f"Error: {e}", DANGER))
    content = re.sub(
        r'app\.after\(0,\s*lambda:\s*toast\.show\(f"Error: \{e\}", DANGER\)\)',
        r'err_str = str(e)\n        app.after(0, lambda err=err_str: toast.show(f"Error: {err}", DANGER))',
        content
    )

    with open(filepath, "w") as f:
        f.write(content)

fix_file("main.py")
fix_file("Ai_AutoTyper_Windows/main.py")

