with open("main.py", "r") as f:
    content = f.read()

replaces = [
    ('app.title("AutoTyper")', 'app.title("AutoTyper Pro + Gemini")'),
    ('app.geometry("900x480")', 'app.geometry("1000x520")'),
    ('ctk.CTkLabel(sidebar, text="AutoTyper",', 'ctk.CTkLabel(sidebar, text="⚡ AutoTyper Pro",'),
    ('text="Type anything, human-speed"', 'text="Gemini-Integrated Code Injection"'),
    ('ctk.CTkLabel(header, text="Text Editor",', 'ctk.CTkLabel(header, text="Payload Editor",'),
    ('PLACEHOLDER       = "// Paste your text here, then press Start (or Cmd+W)"', 'PLACEHOLDER       = "// Paste your code payload here\\n// Or press your configured hotkey to Auto-Solve!"'),
    ('font=(FONT_UI, 22, "bold")', 'font=(FONT_UI, 20, "bold")'),
    ('pady=(0, 28)', 'pady=(0, 30)')
]

for old, new in replaces:
    content = content.replace(old, new)

with open("main.py", "w") as f:
    f.write(content)
