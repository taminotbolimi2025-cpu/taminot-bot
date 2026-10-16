Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\iMaster\.gemini\antigravity-ide\scratch\taminot_task_bot"
WshShell.Run """C:\Users\iMaster\.gemini\antigravity-ide\scratch\taminot_task_bot\.venv\Scripts\python.exe"" ""C:\Users\iMaster\.gemini\antigravity-ide\scratch\taminot_task_bot\bot.py""", 0, False
