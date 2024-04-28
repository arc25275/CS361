import tkinter as tk
from tkinter import ttk

root = tk.Tk()
root.geometry('1200x800')
root.columnconfigure(0, weight=1, uniform="column")
root.columnconfigure(1, weight=1, uniform="column")
root.columnconfigure(2, weight=1, uniform="column")
root.rowconfigure(0, weight=1)


task_container = tk.Frame(root)
task_container.grid(row=0, column=0, sticky='nsew')
task_container.columnconfigure(0, weight=1)
task_container.rowconfigure(0, weight=1)

left_canvas = tk.Canvas(task_container)
left_canvas.grid(row=0, column=0, sticky='nsew')

left_scrollbar = tk.Scrollbar(task_container, orient='vertical', command=left_canvas.yview)
left_scrollbar.grid(row=0, column=1, sticky='nsew')
left_canvas['yscrollcommand'] = left_scrollbar.set

left_canvas.columnconfigure(0, weight=1)
left_canvas.rowconfigure(0, weight=1)

left_final_window = tk.Frame(left_canvas, bg='green')
left_canvas.create_window((0, 0), window=left_final_window, anchor='nw', tags='expand1')
left_final_window.columnconfigure(0, weight=1)

for i in range(1, 51):
    label = tk.Label(left_final_window, text=f'({i})', height=10)
    label.grid(row=i-1, column=0, sticky='nsew', pady=(0, 2))


left_canvas.bind('<Configure>', lambda event: left_canvas.itemconfigure('expand1', width=event.width))
left_final_window.update_idletasks()
left_canvas.config(scrollregion=left_canvas.bbox('all'))

############### Scroll Using Mouse Wheel ###############
def scroll(event, widget):
    widget.yview_scroll(int(-1 * (event.delta / 120)), "units")


def final_scroll(event, widget, func):
    widget.bind_all("<MouseWheel>", func)


def stop_scroll(event, widget):
    widget.unbind_all("<MouseWheel>")


left_canvas.bind("<Enter>", lambda event: final_scroll(event, left_canvas, lambda event: scroll(event, left_canvas)))
left_canvas.bind("<Leave>", lambda event: stop_scroll(event, left_canvas))

right_container = tk.Frame(root, bg='orange')
right_container.grid(row=0, column=1,columnspan=2, sticky='nsew')
right_container.columnconfigure(0, weight=1)
right_container.rowconfigure(0, weight=1)

right_canvas = tk.Canvas(right_container, bg='red')
right_canvas.grid(row=0, column=0, sticky='nsew')

right_canvas.bind_all('<Configure>', lambda event: right_canvas.itemconfigure('expand', width=event.width))


root.mainloop()

root.mainloop()