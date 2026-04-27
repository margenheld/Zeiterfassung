import tkinter as tk


class _Tooltip:
    """Hover-Tooltip an ein beliebiges Tk-Widget binden."""

    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event):
        if self.tip is not None or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self.tip,
            text=self.text,
            background="#1e293b",
            foreground="#e0e0e0",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=4,
            font=("Segoe UI", 9),
        ).pack()

    def _hide(self, _event):
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def attach_tooltip(widget: tk.Widget, text: str) -> None:
    """Bindet ein Tooltip an widget. Mehrfachaufruf erzeugt mehrere Tooltips — Aufrufer ist verantwortlich, das nur einmal pro Widget zu tun."""
    _Tooltip(widget, text)
