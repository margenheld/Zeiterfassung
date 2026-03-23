# src/main.py
from src.storage import Storage
from src.ui import App
import tkinter as tk

def main():
    storage = Storage("zeiterfassung.json")
    root = tk.Tk()
    app = App(root, storage)
    root.mainloop()

if __name__ == "__main__":
    main()
