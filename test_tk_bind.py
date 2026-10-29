import tkinter as tk

def on_press(e):
    print("Pressed:", e.keysym)

root = tk.Tk()
root.bind('<Control-q>', lambda e: print("Ctrl+q triggered!"))
root.bind('<Control-Shift-Q>', lambda e: print("Ctrl+Shift+Q triggered!"))
root.bind('<Control-Shift-q>', lambda e: print("Ctrl+Shift-q triggered!"))
root.bind('<KeyPress>', on_press)
root.after(1000, lambda: root.event_generate('<Control-Shift-KeyPress-Q>'))
root.after(2000, root.destroy)
root.mainloop()
