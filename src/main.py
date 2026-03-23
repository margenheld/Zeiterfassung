# src/main.py
import os
import sys
import tkinter as tk
from src.paths import get_base_path
from src.storage import Storage
from src.settings import Settings
from src.ui import App


def main():
    base = get_base_path()
    storage = Storage(os.path.join(base, "zeiterfassung.json"))
    settings = Settings(os.path.join(base, "settings.json"))

    root = tk.Tk()
    app = App(root, storage, settings, base_path=base)

    if "--minimized" in sys.argv:
        root.iconify()

    root.mainloop()


if __name__ == "__main__":
    main()
