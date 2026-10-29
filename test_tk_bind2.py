import tkinter as tk

root = tk.Tk()
root.bind('<Control-q>', lambda e: print("Ctrl+q triggered!"))
root.bind('<Control-Shift-Q>', lambda e: print("Ctrl+Shift+Q triggered!"))

# Simulate Control+Shift+Q
root.after(500, lambda: root.event_generate('<KeyPress-q>', state=5)) # 5 is Control + Shift (4 + 1)
root.after(1000, root.destroy)
root.mainloop()
