import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import zmq
import json


context = zmq.Context()
print("Connecting to task server…")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

# UI Setup and Shape
root = ctk.CTk()
root.configure(background="gray14")
root.geometry('1200x800')
# Adding columns and rows
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1, uniform="column")
root.columnconfigure(2, weight=1, uniform="column")
root.columnconfigure(3, weight=1, uniform="column")
root.rowconfigure(0, weight=1)
root.rowconfigure(1, weight=5)

# Add container for tasks in left column
task_container = ctk.CTkFrame(root)
task_container.grid(row=1, column=0, sticky='nsew')
task_container.columnconfigure(0, weight=1)
task_container.rowconfigure(0, weight=1)
# Create a canvas that can be scrollable
left_canvas = ctk.CTkCanvas(task_container, bg="gray14", highlightthickness=0)
left_canvas.grid(row=0, column=0, sticky='nsew')
left_scrollbar = ctk.CTkScrollbar(task_container, orientation='vertical', command=left_canvas.yview)
left_scrollbar.grid(row=0, column=1, sticky='nsew')
left_canvas['yscrollcommand'] = left_scrollbar.set
left_canvas['yscrollincrement'] = 30
left_canvas.columnconfigure(0, weight=1)
left_canvas.rowconfigure(0, weight=1)
left_final_window = ctk.CTkFrame(left_canvas)
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
right_container = ctk.CTkFrame(root, bg_color="gray14", fg_color="gray14", width=800)
right_container.grid(row=1, column=1, columnspan=3, sticky='nsew')
right_container.columnconfigure(0, weight=1)
right_container.rowconfigure(0, weight=1)

right_canvas = ctk.CTkCanvas(right_container, bg="gray14", highlightthickness=0)
right_canvas.grid(row=0, column=0, sticky='nsew')


# Allow resizing
# right_canvas.bind_all('<Configure>', lambda event: right_canvas.itemconfigure('expand', width=event.width))

# Get Tasks
payload = {
    "type": "get",
    "path": "tasks/all",
    "data": ""
}
socket.send_string(json.dumps(payload))

response = json.loads(socket.recv_string())
print(response)

if response["response"] == 400:
    print("Server Error")
    tasks = []
else:
    tasks = response["response"]
print(tasks)


# Add tasks to right side
def edit_task(n):
    return 0


task_detail_frames = []


def build_task_details():
    for i in range(len(tasks)):
        # Create a new frame for the task detail view and add it to the list
        task_detail_frame = ctk.CTkFrame(right_canvas, bg_color="gray14", fg_color="gray14")
        task_detail_frames.append(task_detail_frame)

        task_detail_frame.columnconfigure(index=0, weight=1, uniform="column")
        task_detail_frame.columnconfigure(index=1, weight=1, uniform="column")
        task_detail_frame.columnconfigure(index=2, weight=1, uniform="column")
        task_detail_frame.rowconfigure(index=0, weight=1, uniform="row")
        task_detail_frame.rowconfigure(index=1, weight=1, uniform="row")

        # Name
        task_name = ctk.CTkLabel(task_detail_frame, text=f'Task {tasks[i]["id"]} - {tasks[i]["name"]}', font=("Arial", 30), padx=15, pady=10)
        task_name.grid(column=0, row=0, sticky="nw")

        # Completion Checkbox
        complete_frame = ctk.CTkFrame(task_detail_frame, fg_color="gray14")
        complete_text = ctk.CTkLabel(complete_frame, text="Complete ", font=("Arial", 30))
        task_var = ctk.BooleanVar(value=True if tasks[i]["status"] == "closed" else False)
        complete_box = ctk.CTkCheckBox(complete_frame, variable=task_var, text="", checkbox_width=30, checkbox_height=30)
        complete_text.grid(column=0, row=0, sticky="nsew", pady=10)
        complete_box.grid(column=1, row=0, sticky="nsew")
        complete_frame.grid(column=1, row=0, sticky="nse")

        # Editing Button
        edit_button = ctk.CTkButton(task_detail_frame, text="Edit", command=lambda index=i: edit_task(index), font=("Arial", 30), width=80)
        edit_button.grid(column=2, row=0, sticky="nsw", pady=10)

        # Date
        date = ctk.CTkLabel(task_detail_frame, text=tasks[i]["date"], font=("Arial", 30),  fg_color="gray20", corner_radius=10)
        date.grid(row=1, column=0, columnspan=3, sticky="nsw",padx=15, pady=10)

        # Attribute Label
        attribute_label = ctk.CTkLabel(task_detail_frame, text="Attributes", font=("Arial", 30), padx=15)
        attribute_label.grid(row=2, column=0, columnspan=3, sticky="nsw")
        # Attributes
        # New code to create a separate label for each attribute
        max_j = 0
        for j, attr in enumerate(tasks[i]["attributes"]):
            attr_text = f'{attr["name"].strip()}: {attr["value"].strip()}'
            attribute_label = ctk.CTkLabel(task_detail_frame, text=attr_text, font=("Arial", 25),
                                           fg_color="gray20", corner_radius=10)
            attribute_label.grid(row=3+j, column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            task_detail_frame.rowconfigure(index=3+j, weight=1, uniform="row")
            max_j = j

        # Description Label
        description_label = ctk.CTkLabel(task_detail_frame, text="Description", font=("Arial", 30), padx=15)
        description_label.grid(row=max_j+4, column=0, columnspan=3, sticky="nsw")
        # Description
        description = ctk.CTkTextbox(task_detail_frame, font=("Arial", 20), padx=15, wrap='word', width=800,
                                     height=400, spacing2=10)
        description.insert('1.0', tasks[i]["description"])
        description.configure(state="disabled")
        description.grid(row=max_j + 5, column=0, columnspan=3, sticky="nsw", padx=15, pady=10)

        # Create a Scrollbar and attach it to the Text widget
        scrollbar = ctk.CTkScrollbar(task_detail_frame, command=description.yview)
        scrollbar.grid(row=max_j + 5, column=3, sticky='nsew')
        description['yscrollcommand'] = scrollbar.set

        task_detail_frame.rowconfigure(index=max_j+4, weight=1, uniform="row")
        task_detail_frame.rowconfigure(index=max_j+5, weight=0)

        task_detail_frame.grid(row=1, column=1, columnspan=3, sticky='nsew')


def change_task(n):
    # Bring the frame of the selected task detail view to the top
    task_detail_frames[n].tkraise()


def build_task_list():
    # Create Tasks on left side
    for i in range(len(tasks)):
        print(i)
        button = ctk.CTkButton(left_final_window, command=lambda index=i: change_task(index), text="", width=500,
                               height=100)
        button.grid(row=i, column=0, sticky="nsew", pady=1)
        name = ctk.CTkLabel(button, text=f'{tasks[i]["date"]} - {tasks[i]["name"]}', font=("Arial", 20), padx=10, pady=10,
                                  fg_color="transparent", bg_color="transparent")
        name.grid(row=0, column=0, sticky="nsw")
        name.bind("<Button-1>", lambda event, index=i: change_task(index))  # Bind the click event to the label
        filler = ctk.CTkLabel(button, text="")
        filler.grid(row=1, column=0)
        attr_list = ", ".join(attr["value"] for attr in tasks[i]["attributes"])
        attributes = ctk.CTkLabel(button, text=f'{attr_list}', font=("Arial", 20), padx=10, pady=10)
        attributes.grid(row=2, column=0, sticky="nsw")
        attributes.bind("<Button-1>", lambda event, index=i: change_task(index))


build_task_list()
build_task_details()
change_task(0)

# Add menu
menu_bar = ctk.CTkFrame(root)
menu_bar.grid(row=0, column=0, columnspan=4, sticky='nsew')

# Sort & Filter
sorting_button = ctk.CTkButton(menu_bar, text="Sort and Filter", font=("Arial", 20), width=40, height=20)
sorting_button.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)

# Add
add_button = ctk.CTkButton(menu_bar, text="+", font=("Arial", 20),width=20, height=20)
add_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)

# Help Button
help_button = ctk.CTkButton(menu_bar, text="What's New? / Help", font=("Arial", 20), width=20, height=20)
help_button.grid(row=0, column=4, sticky="nsew", pady=10, padx=10)

# Config menu bar grid
menu_bar.columnconfigure(0, weight=1)
menu_bar.columnconfigure(1, weight=1)
menu_bar.columnconfigure(2, weight=4)
menu_bar.columnconfigure(3, weight=4)
menu_bar.columnconfigure(4, weight=1)





root.mainloop()
