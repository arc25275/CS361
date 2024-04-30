import tkinter as tk
from tkinter import ttk
import zmq
import json





context = zmq.Context()
print("Connecting to task server…")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

# UI Setup and Shape
root = tk.Tk()
root.geometry('1200x800')
# Adding columns and rows
root.columnconfigure(0, weight=1, uniform="column")
root.columnconfigure(1, weight=1, uniform="column")
root.columnconfigure(2, weight=1, uniform="column")
root.rowconfigure(0, weight=1)

# Add container for tasks in left column
task_container = tk.Frame(root)
task_container.grid(row=0, column=0, sticky='nsew')
task_container.columnconfigure(0, weight=1)
task_container.rowconfigure(0, weight=1)
# Create a canvas that can be scrollable
left_canvas = tk.Canvas(task_container)
left_canvas.grid(row=0, column=0, sticky='nsew')
left_scrollbar = tk.Scrollbar(task_container, orient='vertical', command=left_canvas.yview)
left_scrollbar.grid(row=0, column=1, sticky='nsew')
left_canvas['yscrollcommand'] = left_scrollbar.set
left_canvas['yscrollincrement'] = 30
left_canvas.columnconfigure(0, weight=1)
left_canvas.rowconfigure(0, weight=1)
left_final_window = tk.Frame(left_canvas, bg='green')
left_canvas.create_window((0, 0), window=left_final_window, anchor='nw', tags='expand1')
left_final_window.columnconfigure(0, weight=1)


left_canvas.bind('<Configure>', lambda event: left_canvas.itemconfigure('expand1', width=event.width))
left_final_window.update_idletasks()
left_canvas.config(scrollregion=left_canvas.bbox('all'))

# Add ability to scroll


def scroll(event, widget):
    widget.yview_scroll(int(-1 * (event.delta / 120)), "units")


def final_scroll(event, widget, func):
    widget.bind_all("<MouseWheel>", func)


def stop_scroll(event, widget):
    widget.unbind_all("<MouseWheel>")

# Make sure scrolling happens in the right place
left_canvas.bind("<Enter>", lambda event: final_scroll(event, left_canvas, lambda event: scroll(event, left_canvas)))
left_canvas.bind("<Leave>", lambda event: stop_scroll(event, left_canvas))

# Creating details panel
right_container = tk.Frame(root, bg='orange')
right_container.grid(row=0, column=1, columnspan=2, sticky='nsew')
right_container.columnconfigure(0, weight=1)
right_container.rowconfigure(0, weight=1)

right_canvas = tk.Canvas(right_container, bg='red')
right_canvas.grid(row=0, column=0, sticky='nsew')

# Allow resizing
right_canvas.bind_all('<Configure>', lambda event: right_canvas.itemconfigure('expand', width=event.width))

# Get Tasks
socket.send_string("all")

response = json.loads(socket.recv_string())
print(response)

if response["response"] == 400:
    print("Server Error")
    tasks = []
else:
    tasks = response["response"]["tasks"]
print(tasks)

# Add tasks to right side

def change_task(n):
    description = tasks[n]["description"]
    label = tk.Label(right_canvas, text=description, font=("Arial", 15))
    label.grid(row=0, column=0, sticky="nsew")
    right_canvas.grid_rowconfigure(0, weight=1)
    right_canvas.grid_columnconfigure(0, weight=1)


# Create Tasks on left side
for i in range(len(tasks)):
    print(i)
    button = tk.Button(left_final_window, text=f'{tasks[i]["name"]}', font=("Arial", 15), command=lambda index=i:
    change_task(index), height=5)
    button.grid(row=i, column=0, sticky='nsew', pady=(0, 2))
change_task(0)

root.mainloop()
