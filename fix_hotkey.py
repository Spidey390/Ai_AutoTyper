with open("main.py", "r") as f:
    content = f.read()

old_logic = """            if is_mod and is_shift and q:
                if not app._ai_hotkey_pressed:
                    app._ai_hotkey_pressed = True
                    on_ai_auto_type()
            elif is_mod and is_shift and e_key:
                if not getattr(app, '_ai_error_hotkey_pressed', False):
                    app._ai_error_hotkey_pressed = True
                    on_ai_error_fix()
            elif is_mod and not is_shift and q:
                if not app._hotkey_pressed:
                    app._hotkey_pressed = True
                    # Delay start_stop slightly to see if the user is rolling into Shift+Q
                    app.after(150, lambda: on_start_stop() if (not app._ai_hotkey_pressed and app._hotkey_pressed) else None)
            else:
                app._hotkey_pressed = False
                app._ai_hotkey_pressed = False
                app._ai_error_hotkey_pressed = False"""

new_logic = """            if is_mod and is_shift and q:
                if not app._ai_hotkey_pressed:
                    app._ai_hotkey_pressed = True
                    on_ai_auto_type()
            elif is_mod and is_shift and e_key:
                if not getattr(app, '_ai_error_hotkey_pressed', False):
                    app._ai_error_hotkey_pressed = True
                    on_ai_error_fix()
            elif is_mod and not is_shift and q:
                if not app._hotkey_pressed and not app._ai_hotkey_pressed:
                    app._hotkey_pressed = True
                    # Delay start_stop slightly to see if the user is rolling into Shift+Q
                    app.after(150, lambda: on_start_stop() if (not app._ai_hotkey_pressed and app._hotkey_pressed) else None)
            else:
                if not (is_mod or q or e_key):
                    app._hotkey_pressed = False
                    app._ai_hotkey_pressed = False
                    app._ai_error_hotkey_pressed = False"""
content = content.replace(old_logic, new_logic)

with open("main.py", "w") as f:
    f.write(content)
