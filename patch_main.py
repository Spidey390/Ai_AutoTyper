import re

with open("main.py", "r") as f:
    content = f.read()

# 1. State variables
content = content.replace(
    "_last_ai_trigger    = 0.0",
    "_last_ai_trigger    = 0.0\nlast_generated_code = \"\""
)

# 2. Add clean_markdown_code
clean_code_func = """
def clean_markdown_code(text):
    import re
    code = text.strip()
    if code.startswith("```"):
        code = re.sub(r"^```[a-zA-Z]*\\n", "", code)
        code = re.sub(r"\\n```$", "", code)
    return code.strip()
"""
content = content.replace("def ai_auto_type_worker():", clean_code_func + "\ndef ai_auto_type_worker():")

# 3. Update ai_auto_type_worker
ai_worker_old = """        code = gemini_client.get_solution(api_key, model, img, progress)
        
        # Remove indentation"""
ai_worker_new = """        code = gemini_client.get_solution(api_key, model, img, progress)
        code = clean_markdown_code(code)
        global last_generated_code
        last_generated_code = code
        
        # Remove indentation"""
content = content.replace(ai_worker_old, ai_worker_new)

# 4. Add ai_error_fix_worker
error_worker = """
def ai_error_fix_worker():
    global typing_active, last_generated_code
    if not last_generated_code.strip():
        app.after(0, lambda: toast.show("No previous code to fix!", DANGER))
        app.after(3000, toast.hide)
        return
        
    api_key = app_config.get("api_key", "").strip()
    if not api_key:
        app.after(0, lambda: toast.show("Please set Gemini API Key in Settings!", DANGER))
        app.after(3000, toast.hide)
        typing_active = False
        app.after(0, lambda: update_ui_state("Failed.", WARNING, False))
        return

    try:
        app.after(0, lambda: update_ui_state("Capturing error screen...", ACCENT, True))
        img, _ = screenshot.capture_screen_image()
        
        def progress(msg):
            app.after(0, lambda: toast.show(msg, ACCENT))
            
        model = app_config.get("model", "gemini-2.5-pro")
        code = gemini_client.get_fixed_solution(api_key, model, img, last_generated_code, progress)
        code = clean_markdown_code(code)
        
        last_generated_code = code

        # Remove indentation
        lines = [line.lstrip() for line in code.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        code = "\\n".join(lines)
        
        if not code.strip():
            raise RuntimeError("Gemini returned no executable code.")
            
        app.after(0, _placeholder_clear)
        app.after(0, lambda: code_box.delete("1.0", ctk.END))
        app.after(0, lambda: code_box.insert("1.0", code))
        
        app.after(0, lambda: update_ui_state("Starting in 2s… Switch to target window!", ACCENT, True))
        time.sleep(2)
        type_code(code, speed_var.get())
    except Exception as e:
        typing_active = False
        app.after(0, lambda: toast.show(f"Error: {e}", DANGER))
        app.after(4000, toast.hide)
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))

def on_ai_error_fix():
    global typing_active, typing_thread, _last_ai_trigger
    now = time.time()
    if now - _last_ai_trigger < 1.0:
        return
    _last_ai_trigger = now
    if typing_active:
        typing_active = False
        app.after(0, lambda: update_ui_state("Stopped.", WARNING, False))
    else:
        typing_active = True
        typing_thread = threading.Thread(target=ai_error_fix_worker, daemon=True)
        typing_thread.start()
"""
content = content.replace("def on_ai_auto_type():", error_worker + "\ndef on_ai_auto_type():")

# 5. UI Button for Error Fix
ai_btn = """ai_btn = ctk.CTkButton(
    sidebar, text="✨  AI Auto-Type  (Ctrl+Shift+Q)", command=on_ai_auto_type,
    font=(FONT_UI, 14, "bold"), fg_color="#8B5CF6",
    hover_color="#7C3AED", height=45,
)
ai_btn.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="ew")"""
ai_error_btn = """
ai_error_btn = ctk.CTkButton(
    sidebar, text="🔧  AI Error Fix  (Ctrl+Shift+E)", command=on_ai_error_fix,
    font=(FONT_UI, 14, "bold"), fg_color="#D97706",
    hover_color="#B45309", height=45,
)
ai_error_btn.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="ew")
"""
content = content.replace(ai_btn, ai_btn + ai_error_btn)
content = content.replace("start_btn.grid(row=4", "start_btn.grid(row=5")
content = content.replace("stop_btn.grid(row=5", "stop_btn.grid(row=6")
content = content.replace("sidebar.grid_rowconfigure(5,", "sidebar.grid_rowconfigure(6,")

# 6. Hotkeys bindings
nsevent_old = """    app.bind("<Command-Q>", lambda e: on_ai_auto_type())
    app._hotkey_pressed = False"""
nsevent_new = """    app.bind("<Command-Q>", lambda e: on_ai_auto_type())
    app.bind("<Control-Shift-e>", lambda e: on_ai_error_fix())
    app.bind("<Control-Shift-E>", lambda e: on_ai_error_fix())
    app.bind("<Command-Shift-e>", lambda e: on_ai_error_fix())
    app.bind("<Command-Shift-E>", lambda e: on_ai_error_fix())
    app._hotkey_pressed = False"""
content = content.replace(nsevent_old, nsevent_new)

# Quartz hotkeys
poll_old = """            q = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 12)
            
            is_mod = (ctrl or ctrl2 or cmd or cmd2)
            is_shift = (shift or shift2)
            
            if is_mod and is_shift and q:"""
poll_new = """            q = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 12)
            e_key = Quartz.CGEventSourceKeyState(Quartz.kCGEventSourceStateHIDSystemState, 14)
            
            is_mod = (ctrl or ctrl2 or cmd or cmd2)
            is_shift = (shift or shift2)
            
            if is_mod and is_shift and q:"""
content = content.replace(poll_old, poll_new)

poll_elif_old = """            elif is_mod and not is_shift and q:"""
poll_elif_new = """            elif is_mod and is_shift and e_key:
                if not getattr(app, '_ai_error_hotkey_pressed', False):
                    app._ai_error_hotkey_pressed = True
                    on_ai_error_fix()
            elif is_mod and not is_shift and q:"""
content = content.replace(poll_elif_old, poll_elif_new)

poll_else_old = """            else:
                app._hotkey_pressed = False
                app._ai_hotkey_pressed = False"""
poll_else_new = """            else:
                app._hotkey_pressed = False
                app._ai_hotkey_pressed = False
                app._ai_error_hotkey_pressed = False"""
content = content.replace(poll_else_old, poll_else_new)

# pynput bindings
pynput_old = """    def on_activate_ai():
        app.after(0, on_ai_auto_type)"""
pynput_new = """    def on_activate_ai():
        app.after(0, on_ai_auto_type)
    def on_activate_error():
        app.after(0, on_ai_error_fix)"""
content = content.replace(pynput_old, pynput_new)

pynput_binds_old = """        '<cmd>+<shift>+Q': on_activate_ai,
        '<cmd>+Q': on_activate_ai
    })"""
pynput_binds_new = """        '<cmd>+<shift>+Q': on_activate_ai,
        '<cmd>+Q': on_activate_ai,
        '<ctrl>+<shift>+e': on_activate_error,
        '<ctrl>+<shift>+E': on_activate_error,
        '<cmd>+<shift>+e': on_activate_error,
        '<cmd>+<shift>+E': on_activate_error
    })"""
content = content.replace(pynput_binds_old, pynput_binds_new)

with open("main.py", "w") as f:
    f.write(content)
