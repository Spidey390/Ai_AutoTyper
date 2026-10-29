import re

with open("Ai_AutoTyper_Windows/main.py", "r") as f:
    content = f.read()

old_except = """        except Exception as e:
            app.after(0, lambda: toast.show(f"❌ Error: {str(e)}", DANGER))
            processing_gemini = False"""
new_except = """        except Exception as e:
            print("ERROR IN GEMINI PIPELINE:", str(e))
            err_msg = str(e)
            app.after(0, lambda err=err_msg: toast.show(f"❌ Error: {err}", DANGER))
            processing_gemini = False"""

content = content.replace(old_except, new_except)

with open("Ai_AutoTyper_Windows/main.py", "w") as f:
    f.write(content)
