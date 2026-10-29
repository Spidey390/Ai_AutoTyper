import re

with open("Ai_AutoTyper_Windows/main.py", "r") as f:
    content = f.read()

# Replace sidebar header
sidebar_header_old = """ctk.CTkLabel(sidebar, text="⚡ AutoTyper Pro",
             font=("Segoe UI", 20, "bold"), text_color="white").grid(
    row=0, column=0, padx=20, pady=(30, 5), sticky="w")
ctk.CTkLabel(sidebar, text="Gemini-Integrated Code Injection",
             font=("Segoe UI", 12), text_color=TEXT_MUTED).grid(
    row=1, column=0, padx=20, pady=(0, 30), sticky="w")"""

sidebar_header_new = """sidebar_header = ctk.CTkFrame(sidebar, fg_color="transparent")
sidebar_header.grid(row=0, column=0, padx=20, pady=(30, 4), sticky="ew")
sidebar_header.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(sidebar_header, text="⚡ AutoTyper Pro",
             font=("Segoe UI", 20, "bold"), text_color="white").grid(row=0, column=0, sticky="w")

settings_btn = ctk.CTkButton(sidebar_header, text="⚙️", width=30, height=30,
                             fg_color="transparent", hover_color="#2D3748", text_color="white", font=("Segoe UI", 18),
                             command=lambda: open_settings())
settings_btn.grid(row=0, column=1, sticky="e")

ctk.CTkLabel(sidebar, text="Gemini-Integrated Code Injection",
             font=("Segoe UI", 12), text_color=TEXT_MUTED).grid(
    row=1, column=0, padx=20, pady=(0, 30), sticky="w")"""
content = content.replace(sidebar_header_old, sidebar_header_new)

# Add open_settings function after the slider
open_settings_func = """
def save_config_file(data):
    import json
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)

def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title("Settings")
    settings_win.geometry("400x300")
    settings_win.configure(fg_color=BG_COLOR)
    settings_win.attributes("-topmost", True)
    
    current_config = load_config()
    
    ctk.CTkLabel(settings_win, text="Settings", font=("Segoe UI", 20, "bold"), text_color="white").pack(pady=(20, 10))
    
    ctk.CTkLabel(settings_win, text="Gemini API Key", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", padx=30)
    api_entry = ctk.CTkEntry(settings_win, width=340, fg_color=PANEL_COLOR, border_color="#2D3748", show="*")
    api_entry.pack(padx=30, pady=(5, 15))
    api_entry.insert(0, current_config.get("api_key", ""))
    
    ctk.CTkLabel(settings_win, text="Model", font=("Segoe UI", 12), text_color=TEXT_MUTED).pack(anchor="w", padx=30)
    model_var = ctk.StringVar(value=current_config.get("model", "gemini-2.5-pro"))
    model_dropdown = ctk.CTkOptionMenu(settings_win, variable=model_var,
                                       values=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp"],
                                       width=340, fg_color=PANEL_COLOR, button_color=ACCENT, button_hover_color="#2563EB")
    model_dropdown.pack(padx=30, pady=(5, 20))
    
    def save_settings():
        current_config["api_key"] = api_entry.get().strip()
        current_config["model"] = model_var.get()
        save_config_file(current_config)
        toast.show("Settings saved!", SUCCESS)
        app.after(2000, toast.hide)
        settings_win.destroy()
        
    save_btn = ctk.CTkButton(settings_win, text="Save Settings", command=save_settings,
                             font=("Segoe UI", 14, "bold"), fg_color=ACCENT, hover_color="#2563EB", height=40)
    save_btn.pack(padx=30, pady=10, fill="x")

create_slider(settings_frame, "Typing Speed (WPM)", speed_var, 10, 500)
"""

content = content.replace('create_slider(settings_frame, "Typing Speed (WPM)", speed_var, 10, 500)\n', open_settings_func)

with open("Ai_AutoTyper_Windows/main.py", "w") as f:
    f.write(content)
