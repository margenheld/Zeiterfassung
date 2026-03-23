# src/main.py
from src.storage import Storage
from src.settings import Settings
from src.ui import App
import tkinter as tk

def main():
    storage = Storage("zeiterfassung.json")
    settings = Settings("settings.json")
    root = tk.Tk()
    app = App(root, storage, settings)
    root.mainloop()

if __name__ == "__main__":
    main()
