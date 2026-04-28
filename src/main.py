# src/main.py
import logging
import os
import sys
import tkinter as tk

from src.logging_setup import setup_logging
from src.paths import get_base_path
from src.settings import Settings
from src.storage import Storage
from src.ui import App
from src.version import VERSION


def main():
    base = get_base_path()
    try:
        setup_logging(base)
        logging.getLogger(__name__).info("Zeiterfassung v%s gestartet", VERSION)
    except Exception:
        # Logging-Setup-Fehler (z.B. Permission-Denied auf logs/, exotisches FS):
        # die App soll trotzdem starten. Ohne Logfile haben wir kein
        # File-Logging, aber der globale Excepthook ist nicht installiert —
        # uncaught Exceptions schreiben auf stderr (im Repo-Mode sichtbar,
        # im Frozen-Mode mit --noconsole verschluckt). Akzeptabler Fallback.
        pass

    storage = Storage(os.path.join(base, "zeiterfassung.json"))
    settings = Settings(os.path.join(base, "settings.json"))

    root = tk.Tk()
    app = App(root, storage, settings, base_path=base)

    if "--minimized" in sys.argv:
        root.iconify()

    root.mainloop()


if __name__ == "__main__":
    main()
