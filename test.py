import matplotlib.pyplot as plt
from itertools import islice
from typing import Callable
import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Add this import


def ones(x: int) -> int:
    return bin(x).count("1")


def findn(func: Callable[[int], int]):
    n = 1
    while True:
        if func(n) == 0:
            print("match!", n)
            yield n
        n += 1


def mksetf(c: int, r: int) -> Callable[[int], int]:
    def setf(n: int) -> int:
        # sure false if r > n
        return ones(c + n) * r - n

    return setf


def update_plot():
    c_value = c_entry.get()
    r_value = r_entry.get()

    # Validate c and r values
    if not c_value or not r_value:
        # Handle empty entries
        return

    try:
        c = int(c_value)
        r = int(r_value)
    except ValueError:
        # Handle non-integer inputs
        return

    setfi = mksetf(c, r)
    n_values = list(range(1, l + 1))
    setf_values = [setfi(n) for n in n_values]

    ax.clear()
    ax.scatter(n_values, setf_values, marker=".", s=5, label="setf(n)")
    ax.plot(
        n_values, setf_values, label="Connect with lines", linestyle="-", linewidth=0.5
    )
    ax.set_title(f"mksetf(c={c}, r={r})")
    ax.set_xlabel("n")
    ax.set_ylabel("setf(n)")
    ax.grid(True)
    ax.legend()

    canvas.draw()


# Create a Tkinter window
root = tk.Tk()
root.title("mksetf GUI")

# Create labels and entry fields for c and r
c_label = ttk.Label(root, text="c:")
c_label.grid(row=0, column=0)
c_entry = ttk.Entry(root)
c_entry.grid(row=0, column=1)

r_label = ttk.Label(root, text="r:")
r_label.grid(row=1, column=0)
r_entry = ttk.Entry(root)
r_entry.grid(row=1, column=1)

# Button to update the plot
update_button = ttk.Button(root, text="Update Plot", command=update_plot)
update_button.grid(row=2, columnspan=2)

# Create a Matplotlib figure and canvas for the plot
l = 100000
fig, ax = plt.subplots(figsize=(15, 10))
canvas = FigureCanvasTkAgg(fig, master=root)
canvas_widget = canvas.get_tk_widget()
canvas_widget.grid(row=3, columnspan=2)

# Initial plot
update_plot()

try:
    root.mainloop()
except KeyboardInterrupt:
    root.destroy()
