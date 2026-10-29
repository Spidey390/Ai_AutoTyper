import re

with open("main.py", "r") as f:
    content = f.read()

# 1. Replace the API key entry in sidebar with just the slider.
settings_frame_old = """create_slider(settings_frame, "Typing Speed (WPM)", speed_var, 10, 500)

ctk.CTkLabel(settings_frame, text="Gemini API Key", font=(FONT_UI, 12),
             text_color=TEXT_MUTED).pack(anchor="w", pady=(5, 0))
api_key_var = ctk.StringVar(value=app_config.get("api_key", ""))
def save_api_key(*args):
    app_config["api_key"] = api_key_var.get()
    save_config(app_config)
api_key_var.trace_add("write", save_api_key)
api_key_entry = ctk.CTkEntry(settings_frame, textvariable=api_key_var, show="*",
                             fg_color=PANEL_COLOR, border_color="#2D3748")
api_key_entry.pack(fill="x", pady=(0, 15))"""

settings_frame_new = """create_slider(settings_frame, "Typing Speed (WPM)", speed_var, 10, 500)

def open_settings():
    settings_win = ctk.CTkToplevel(app)
    settings_win.title("Settings")
    settings_win.geometry("400x300")
    settings_win.configure(fg_color=BG_COLOR)
    settings_win.attributes("-topmost", True)
    
    ctk.CTkLabel(settings_win, text="Settings", font=(FONT_UI, 20, "bold"), text_color="white").pack(pady=(20, 10))
    
    ctk.CTkLabel(settings_win, text="Gemini API Key", font=(FONT_UI, 12), text_color=TEXT_MUTED).pack(anchor="w", padx=30)
    api_entry = ctk.CTkEntry(settings_win, width=340, fg_color=PANEL_COLOR, border_color="#2D3748", show="*")
    api_entry.pack(padx=30, pady=(5, 15))
    api_entry.insert(0, app_config.get("api_key", ""))
    
    ctk.CTkLabel(settings_win, text="Model", font=(FONT_UI, 12), text_color=TEXT_MUTED).pack(anchor="w", padx=30)
    model_var = ctk.StringVar(value=app_config.get("model", "gemini-2.5-pro"))
    model_dropdown = ctk.CTkOptionMenu(settings_win, variable=model_var,
                                       values=["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-pro-exp"],
                                       width=340, fg_color=PANEL_COLOR, button_color=ACCENT, button_hover_color="#2563EB")
    model_dropdown.pack(padx=30, pady=(5, 20))
    
    def save_settings():
        app_config["api_key"] = api_entry.get().strip()
        app_config["model"] = model_var.get()
        save_config(app_config)
        toast.show("Settings saved!", SUCCESS)
        app.after(2000, toast.hide)
        settings_win.destroy()
        
    save_btn = ctk.CTkButton(settings_win, text="Save Settings", command=save_settings,
                             font=(FONT_UI, 14, "bold"), fg_color=ACCENT, hover_color="#2563EB", height=40)
    save_btn.pack(padx=30, pady=10, fill="x")"""
content = content.replace(settings_frame_old, settings_frame_new)

# 2. Add Settings Icon in Sidebar
sidebar_header_old = """ctk.CTkLabel(sidebar, text="⚡ AutoTyper Pro",
             font=(FONT_UI, 20, "bold"), text_color="white").grid(
    row=0, column=0, padx=20, pady=(30, 4), sticky="w")
ctk.CTkLabel(sidebar, text="Gemini-Integrated Code Injection",
             font=(FONT_UI, 12), text_color=TEXT_MUTED).grid(
    row=1, column=0, padx=20, pady=(0, 30), sticky="w")"""

sidebar_header_new = """sidebar_header = ctk.CTkFrame(sidebar, fg_color="transparent")
sidebar_header.grid(row=0, column=0, padx=20, pady=(30, 4), sticky="ew")
sidebar_header.grid_columnconfigure(0, weight=1)

ctk.CTkLabel(sidebar_header, text="⚡ AutoTyper Pro",
             font=(FONT_UI, 20, "bold"), text_color="white").grid(row=0, column=0, sticky="w")

settings_btn = ctk.CTkButton(sidebar_header, text="⚙️", width=30, height=30,
                             fg_color="transparent", hover_color="#2D3748", text_color="white", font=(FONT_UI, 18),
                             command=open_settings)
settings_btn.grid(row=0, column=1, sticky="e")

ctk.CTkLabel(sidebar, text="Gemini-Integrated Code Injection",
             font=(FONT_UI, 12), text_color=TEXT_MUTED).grid(
    row=1, column=0, padx=20, pady=(0, 30), sticky="w")"""
content = content.replace(sidebar_header_old, sidebar_header_new)

with open("main.py", "w") as f:
    f.write(content)
