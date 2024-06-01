import customtkinter as ctk  # Custom tkinter library. Better visuals by default.
import tkinter as tk
import zmq  # Communication with microservices
import json  # Decoding and Encoding messages to microservices
from typing import Self  # Added so functions could properly hint at returning self
import logging  # Custom logger with easier to read colors and easier to control levels of information.
import sys
import argparse  # Used to enable debug logging
# TODO: When functions are done, improve docstring with more info


class CustomFormatter(logging.Formatter):
    """Custom formatter for logging. Will color code based on level of logging"""
    grey = "\x1b[38;20m"
    blue = "\x1b[36m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(name)s:%(funcName)s:(l:%(lineno)d) - %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class LoggingHandler:
    """A class to handle logging for all classes that inherit from it. Will set up logging for each class"""
    def __init__(self, *args, **kwargs):
        # Be able to enable debug if needed
        parser = argparse.ArgumentParser()
        parser.add_argument('--debug',
                            help='Enable debug logging', action='store_true')
        args = parser.parse_args()
        # Set up formatter and logger

        self.custom_formatter = CustomFormatter()
        self.log = logging.getLogger(self.__class__.__name__)
        if self.log.hasHandlers():
            self.log.handlers.clear()
        self.log.propagate = False
        # create console handler with a higher log level
        ch = logging.StreamHandler(stream=sys.stdout)
        if args.debug:
            ch.setLevel(logging.DEBUG)
            self.log.setLevel(logging.DEBUG)
        else:
            ch.setLevel(logging.INFO)
            self.log.setLevel(logging.INFO)
        ch.setFormatter(self.custom_formatter)
        self.log.addHandler(ch)


class AttributeRecord(LoggingHandler):
    def __init__(self, client, attr_id, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: Client = client
        self.id: int = attr_id
        self.name: str = name
        self.record = None

    def __str__(self):
        return f"ID:{self.id} ({self.name})"

    def delete(self) -> bool:
        """Delete attribute from server
        :return: True if successful, False if not
        """
        response = self.client.connection.delete(f"attributes/{self.id}", "")
        if response["code"] == 200:
            self.client.attribute_records.remove(self)
            self.log.debug(f"Attribute deleted from server: {self}")
            return True
        else:
            self.log.error(f"Error deleting attribute: {response["code"]} : {response["message"]}")
            return False

    def build_record_option(self, parent, task) -> dict:
        # tkLayout
        #  attr_frame #[[attr_record_frame]]
        #  > attr_name
        #  > attr_value
        #  > add_button
        attr_frame = ctk.CTkFrame(parent, bg_color="gray14", fg_color="gray14")
        attr_frame.columnconfigure(0, weight=1)
        attr_frame.columnconfigure(1, weight=1)
        attr_frame.columnconfigure(2, weight=1)

        attr_name = ctk.CTkTextbox(attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                                   fg_color="gray20", wrap="none", corner_radius=10, )
        attr_name.insert('1.0', f'{self.name}')
        attr_name.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)

        attr_value = ctk.CTkTextbox(attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                                    fg_color="royal blue", wrap="none", corner_radius=10)
        attr_value.insert('1.0', "value")
        attr_value.grid(row=0, column=1, sticky="nsw", pady=10, padx=10)

        add_button = ctk.CTkButton(attr_frame, text="Add", font=("Arial", 25), width=80, bg_color="gray20", command=lambda: task.add_attribute(self.id, attr_value.get("1.0", "end-1c")))
        add_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)
        # add_button.bind("<Button-1>", lambda: task.add_attribute(self.id, attr_value.get("1.0", "end-1c")))
        option = {
            "type": "new",
            "frame": attr_frame,
            "name": attr_name,
            "value": attr_value,
            "add": add_button
        }
        self.log.debug(f"Existing attribute option built with [{self}]: {option}")
        self.record = option
        return option


class Attribute(AttributeRecord):
    """Attribute for tasks. Can belong to a task, or be standalone"""
    def __init__(self, client, attr_id, name, value, task=None, *args, **kwargs):
        super().__init__(client, attr_id, name, *args, **kwargs)
        self.client: Client = client
        self.id: int = attr_id
        self.name: str = name
        self.value: str = value
        self.task: Task = task
        self.label = self.build_label(self.task.detail_view["frame"]) if self.task is not None else None
        self.option = self.build_current_option(self.task.options_frame) if self.task is not None else None
        self.log.info(f"Attribute created: {self}")

    def __str__(self):
        return f"ID:{self.id} ({self.name} - {self.value} - [{self.task}])"

    def edit(self, new_value: str) -> Self | None:
        """Edit attribute value
        :param new_value: New value to replace previous
        :return: Updated attribute
        """
        response = self.client.connection.put(f"tasks/{self.task.id}/attributes", {"id": self.id, "value": new_value})
        if response["code"] == 200:
            self.value = new_value
            if self.task is not None:
                self.label.configure(text=f'{self.name}: {self.value}')
                self.option["value"].delete("1.0", "end")
                self.option["value"].insert("1.0", f'{self.value}')
                self.log.debug(f"Attribute updated to {self}")
            return self
        else:
            self.log.error(f"Error updating attribute: {response["code"]} : {response["message"]}")
            return None

    def update_value_temp(self, value: str):
        """Update the value of the attribute temporarily while typing
            :param value: The new value of the attribute
            """
        self.value = value

    def remove(self) -> bool:
        """Remove attribute from task, and make it ready to delete.
        :return: True if successful, False if not
        """
        if self.task is None:
            self.log.warning("No task to remove attribute from")
            return False

        # Remove the attribute from the task
        response = self.client.connection.delete(f"tasks/{self.task.id}/attributes/", {"id": self.id})
        if response["code"] == 200:
            self.task.attributes = [attr for attr in self.task.attributes if attr.id != self.id]
            self.log.debug(f"Attribute removed from task: {self}")
            return True
        else:
            self.log.error(f"Error removing attribute: {response["code"]} : {response["message"]}")
            return False

    def build_label(self, parent) -> ctk.CTkLabel:
        """Build the label for the attribute
        :param parent: Parent of the label
        :return: Completed label
        """
        attr_text = f'{self.name}: {self.value}'
        attribute_label = ctk.CTkLabel(parent, text=attr_text, font=("Arial", 25),
                                       fg_color="gray20", corner_radius=10, height=50, padx=10, pady=10)
        self.log.debug(f"Attribute label built with text [{attr_text}]: {attribute_label}")
        return attribute_label

    def build_current_option(self, parent) -> dict:
        """Build the option for the attribute
        :param parent: Parent of the option
        :return: Completed option with all parts, and status. Will include frame, name, value, and remove button
        """
        # tkLayout
        #  attr_frame #[[attr_frame]]
        #  > attr_name
        #  > attr_value
        #  > remove_button
        attr_frame = ctk.CTkFrame(parent, bg_color="gray14", fg_color="gray14", height=50)
        attr_frame.columnconfigure(0, weight=1)
        attr_frame.columnconfigure(1, weight=1)
        attr_frame.columnconfigure(2, weight=1)

        attr_name = ctk.CTkLabel(attr_frame, text=f'{self.name}', font=("Arial", 25),
                                 fg_color="gray20", corner_radius=10, padx=10, pady=10, height=50)
        attr_name.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)
        attr_value = ctk.CTkTextbox(attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                                    fg_color="royal blue", wrap="none")
        # On Typing, update the attribute
        attr_value.bind("<KeyRelease>", lambda val: self.update_value_temp(attr_value.get("1.0", "end-1c")))
        attr_value.insert('1.0', f'{self.value}')
        attr_value.grid(row=0, column=1, sticky="nsw", pady=10, padx=10)

        remove_button = ctk.CTkButton(attr_frame, text="Remove", font=("Arial", 25), width=80, bg_color="gray20", command=lambda: self.task.remove_attribute(self.id))
        remove_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)
        # remove_button.bind("<Button-1>", lambda: self.task.remove_attribute(self.id))
        option = {
            "type": "current",
            "frame": attr_frame,
            "name": attr_name,
            "value": attr_value,
            "remove": remove_button
        }
        self.log.debug(f"Current attribute option built with [{self}]: {option}")
        return option


class Task(LoggingHandler):
    """TODO TASK DOCSTRING"""

    def __init__(self, client, task_id, name, date, attributes, description, status, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client: Client = client
        self.id: int = task_id
        self.name: str = name
        self.date: str = date
        self.description: str = description
        self.attributes: list[Attribute] = attributes
        self.options_frame = None
        self.assign_attributes()
        self.status: str = status
        self.list_item = self.build_list_item(self.client.task_container)
        self.detail_view = self.build_detail_view(self.client.detail_container)
        self.options_frame = ctk.CTkFrame(self.detail_view["frame"], bg_color="gray14", fg_color="gray14")
        self.assign_attributes()
        self.attribute_options = self.build_attribute_options(self.options_frame)
        self.options_open = False
        self.editing = False
        self.log.info(f"Task created: {self}")

    def __str__(self):
        attr_list = [f'{attr.id}:{attr.name}' for attr in self.attributes]
        return f"ID:{self.id} ({self.name} - {self.date} - {self.description} - {attr_list} - {self.status})"

    # Update Data

    def edit(self, new_data) -> Self | None:
        """Edit task with new data
        :param new_data: The new data for the task. Will include the new name, date, description, and attributes
        :return: Updated task if successful, None if not
        """
        # Compare new data to old data
        response = self.client.connection.put(f"tasks/{self.id}", new_data)
        if response["code"] == 200:
            for key, value in new_data.items():
                if self.__dict__[key] != value:
                    self.__dict__[key] = value
                    if key == "name":
                        self.list_item["name"].configure(text=f'{self.date} - {self.name}')
                    if key == "date":
                        self.list_item["name"].configure(text=f'{self.date} - {self.name}')
                    if key == "attributes":
                        attr_list = ", ".join(attr.value for attr in self.attributes)
                        self.list_item["attributes"].configure(text=f'{attr_list}')
            self.log.debug(f"Task updated to {self}")
            return self
        else:
            self.log.error(f"Error updating task: {response["code"]} : {response["message"]}")
            return None

    def delete(self) -> bool:
        """Delete task from server
        :return: True if successful, False if not
        """
        response = self.client.connection.delete(f"tasks/{self.id}", "")
        if response["code"] == 200:
            for attr in self.attributes:
                attr.remove()
                del attr
            self.client.tasks.remove(self)

            self.log.debug(f"Task deleted: {self}")
            return True
        else:
            self.log.error(f"Error deleting task: {response["code"]} : {response["message"]}")
            return False

    def toggle_active(self) -> str:
        """Toggle task status between active and complete
        :return: New status
        """
        if self.status == "open":
            self.status = "closed"
        else:
            self.status = "open"
        self.edit({
            "status": self.status
        })
        self.log.debug(f"Task status toggled to {self.status}")
        return self.status

    # UI
    def build_list_item(self, parent) -> dict:
        """Build the list item that shows on the left side. Will include name, date, and attributes
        :param parent: Parent of the CtkButton
        :return: UI item
        """
        # tkLayout
        #  button #[[button]]
        #  > name
        #  > filler
        #  > attributes
        button = ctk.CTkButton(parent, command=lambda index=self.id: self.client.change_task(index), text="", width=400,
                               height=100)
        if self.status == "closed":
            button.configure(bg_color="gray14", fg_color="gray20")

        # Name for task title
        name = ctk.CTkLabel(button, text=f'{self.date} - {self.name}', font=("Arial", 20), padx=10, pady=10,
                            fg_color="transparent", bg_color="transparent")
        name.grid(row=0, column=0, sticky="nsw")
        # Bind the click event to the label, so you can click anywhere on the task
        name.bind("<Button-1>", lambda event, index=self.id: self.client.change_task(index))

        # Filler for checkmark and empty space
        filler = ctk.CTkLabel(button, text="", padx=10)
        if self.status == "closed":
            filler.configure(text="✓", font=("Arial", 20))
        filler.grid(row=1, column=0, sticky="w")

        # Attributes for task
        attr_list = ", ".join(attr.value for attr in self.attributes)
        attributes = ctk.CTkLabel(button, text=f'{attr_list}', font=("Arial", 20), padx=10, pady=10)
        attributes.grid(row=2, column=0, sticky="nsw")
        attributes.bind("<Button-1>", lambda event, index=self.id: self.client.change_task(index))
        list_item = {
            "button": button,
            "filler": filler,
            "name": name,
            "attributes": attributes
        }
        self.log.debug(f"Task list item built with [{self}]: {list_item}")
        return list_item

    def build_detail_view(self, parent):
        """TODO:Build task detail view"""
        # tkLayout
        #  task_detail_frame #[[task_detail_frame]]
        #  > name_frame
        #    > name_label
        #    > task_name
        #  > complete_frame
        #    > complete_text
        #    > complete_box
        #  > edit_button
        #  > date
        #  > attribute_label
        #  > attributes
        #  > description_label
        #  > description
        # Create a new frame for the task detail view and add it to the list
        task_detail_frame = ctk.CTkFrame(parent, bg_color="gray14", fg_color="gray14", height=800)

        task_detail_frame.columnconfigure(index=0, weight=1, uniform="column")
        task_detail_frame.columnconfigure(index=1, weight=1)
        task_detail_frame.columnconfigure(index=2, weight=1, uniform="column")
        task_detail_frame.rowconfigure(index=0, weight=1)
        task_detail_frame.rowconfigure(index=1, weight=1)

        # Name Frame
        name_frame = ctk.CTkFrame(task_detail_frame, bg_color="gray14", fg_color="gray14")
        name_frame.grid(row=0, column=0, sticky="nsw")
        name_frame.columnconfigure(0, weight=1)
        name_frame.columnconfigure(1, weight=1)

        # Name Label
        name_label = ctk.CTkLabel(name_frame, text=f'Task {self.id+1} - ', font=("Arial", 30))

        # Name Textbox
        task_name = ctk.CTkTextbox(name_frame, font=("Arial", 30), border_width=0,
                                   height=1, width=300, fg_color="gray14", wrap="none")
        task_name.insert('1.0', f'{self.name}')
        task_name.configure(state="disabled")
        task_name.grid(row=0, column=1, sticky="nsw", pady=10)

        name_label.grid(row=0, column=0, sticky="nsw", padx=(10, 0))

        # Completion Checkbox
        complete_frame = ctk.CTkFrame(task_detail_frame, fg_color="gray14", width=100)
        complete_text = ctk.CTkLabel(complete_frame, text="Complete ", font=("Arial", 30))
        task_var = ctk.BooleanVar(value=True if self.status == "closed" else False)
        complete_box = ctk.CTkCheckBox(complete_frame, variable=task_var,
                                       command=lambda: self.client.toggle_active(self.id),
                                       text="",
                                       checkbox_width=30,
                                       checkbox_height=30)
        complete_text.grid(column=0, row=0, sticky="nsew", pady=10)
        complete_box.grid(column=1, row=0, sticky="nsew")
        complete_frame.grid(column=1, row=0, sticky="nsw", pady=10, padx=10)

        # Editing Button
        edit_button = ctk.CTkButton(task_detail_frame, text="Edit", command=lambda: self.client.edit_task(self.id),
                                    font=("Arial", 30), width=80, bg_color="gray14")
        edit_button.grid(column=2, row=0, sticky="nsw", pady=10)

        # Date
        date = ctk.CTkTextbox(task_detail_frame, font=("Arial", 30), border_width=0, height=1,
                              width=175,
                              fg_color="gray20", wrap="none")
        date.insert('1.0', self.date)
        date.configure(state="disabled")
        date.grid(row=1, column=0, columnspan=3, sticky="nsw", padx=15, pady=10)

        # Attribute Label
        attribute_label = ctk.CTkButton(task_detail_frame, text="Attributes", font=("Arial", 30),
                                        command=lambda: self.client.toggle_attribute_options(self.id),
                                        state="disabled", bg_color="gray14", fg_color="gray14", text_color="white", text_color_disabled="white")
        attribute_label.grid(row=2, column=0, columnspan=3, sticky="nsw", pady=10, padx=15)
        # Attributes
        max_j = 6
        for attr in self.attributes:
            if attr.label is None:
                attr.label = attr.build_label(task_detail_frame)
            attr.label.grid(row=max_j, column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            max_j += 1
        attribute_row = max_j
        max_j += 50  # This gives space for new attributes. It feels a bit messy, but right now its the best way to do it.
        # Description Label
        description_label = ctk.CTkLabel(task_detail_frame, text="Description", font=("Arial", 30), padx=15)
        description_label.grid(row=max_j, column=0, columnspan=3, sticky="nsw")
        max_j += 1
        # Description
        description = ctk.CTkTextbox(task_detail_frame, font=("Arial", 20), padx=15, wrap='word', width=800,
                                     height=300, spacing2=10)
        description.insert('1.0', self.description)
        description.configure(state="disabled")
        description.grid(row=max_j, column=0, columnspan=3, sticky="nsw", padx=15, pady=10)
        max_j += 1

        # Create a Scrollbar and attach it to the Text widget
        scrollbar = ctk.CTkScrollbar(task_detail_frame, command=description.yview)
        scrollbar.grid(row=max_j, column=3, sticky='nsew')
        max_j += 1
        description['yscrollcommand'] = scrollbar.set

        task_detail_frame.rowconfigure(index=max_j - 1, weight=1)
        task_detail_frame.rowconfigure(index=max_j, weight=1)


        self.log.debug(f"Task detail view built: {task_detail_frame}")
        return {
            "attr_row": attribute_row,
            "name": task_name,
            "date": date,
            "description": description,
            "complete": complete_box,
            "edit": edit_button,
            "attributes": attribute_label,
            "frame": task_detail_frame
        }

    def build_attribute_options(self, attr_options_frame):
        """TODO:Build attribute options for task. Hide below task details"""

        attr_options_frame.columnconfigure(0, weight=1)
        attr_options_frame.columnconfigure(1, weight=1)
        attr_options_frame.columnconfigure(2, weight=1)

        # Current Attr Label
        current_attr_label = ctk.CTkLabel(attr_options_frame, text="Current Attributes", font=("Arial", 30), padx=15)
        current_attr_label.grid(row=0, column=0, sticky="nsw")

        current_attr_options = []
        # Current Attributes
        max_i = 1
        for attr in self.attributes:
            option = attr.option
            option["frame"].grid(row=max_i, column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            current_attr_options.append({attr.id: option})
            max_i += 1
        current_row = max_i + 1
        max_i += 50

        # Find existing attributes that aren't already in the task
        existing_attributes = []
        for i, attr in enumerate(self.client.attribute_records):
            if attr.id not in [a.id for a in self.attributes]:
                existing_attributes.append(attr)

        existing_attr_label = None
        existing_attr_options = []

        # Existing Attr Label
        if len(existing_attributes) > 0:
            existing_attr_label = ctk.CTkLabel(attr_options_frame, text="Existing Attributes", font=("Arial", 30),
                                               padx=15)
            existing_attr_label.grid(row=max_i, column=0, sticky="nsw")
            max_i += 1
            # Existing Attributes
            for attr in existing_attributes:
                option = attr.build_record_option(attr_options_frame, self)
                option["frame"].grid(row=max_i, column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
                existing_attr_options.append({attr.id: option})
                max_i += 1
        existing_row = max_i + 1
        max_i += 50

        # New Attr Label (Just 2 blank textboxes and a button to add. If one is added, add another)
        new_attr_label = ctk.CTkLabel(attr_options_frame, text="New Attributes", font=("Arial", 30), padx=15)
        new_attr_label.grid(row=max_i, column=0, sticky="nsw")
        max_i += 1
        new_attr_frame = ctk.CTkFrame(attr_options_frame, bg_color="gray14", fg_color="gray14")
        new_attr_frame.grid(row=max_i, column=0, columnspan=3, sticky="nsw")
        max_i += 1
        new_attr_frame.columnconfigure(0, weight=1)
        new_attr_frame.columnconfigure(1, weight=1)
        new_attr_frame.columnconfigure(2, weight=1)
        new_attr_name = ctk.CTkTextbox(new_attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                                       fg_color="royal blue", wrap="none", corner_radius=10)
        new_attr_name.insert('1.0', "name")
        new_attr_name.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)
        new_attr_value = ctk.CTkTextbox(new_attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                                        fg_color="royal blue", wrap="none", corner_radius=10)
        new_attr_value.insert('1.0', "value")
        new_attr_value.grid(row=0, column=1, sticky="nsw", pady=10, padx=10)
        add_button = ctk.CTkButton(new_attr_frame, text="Add", font=("Arial", 25), width=80, bg_color="gray14",
                                   corner_radius=10)
        add_button.grid(row=0, column=2, sticky="nsw")
        add_button.bind("<Button-1>", lambda event: self.create_attribute(new_attr_name.get("1.0", "end-1c"),
                                                                  new_attr_value.get("1.0", "end-1c")))
        return {
            "current_row": current_row,
            "current_label": current_attr_label,
            "current_options": current_attr_options,
            "existing_row": existing_row,
            "existing_label": existing_attr_label,
            "existing_options": existing_attr_options,
            "new": new_attr_label,
            "new_name": new_attr_name,
            "new_value": new_attr_value,
            "frame": attr_options_frame
        }

    def assign_attributes(self) -> bool:
        """Assign attributes to task
        :return: True if successful, False if not
        """
        for attr in self.attributes:
            attr.task = self
            if self.options_frame is not None and attr.option is None:
                attr.option = attr.build_current_option(self.options_frame)
            self.log.debug(f"Attribute {attr.id} assigned to task with value {attr.value}")
        return True

    # Manage Attributes
    def create_attribute(self, name: str, value: str) -> Attribute | None:
        # TODO: Update options
        """Create an entirely new attribute, and add it to the task
        :param name: Name to be used
        :param value: Value to be used
        :return: Attribute if successful, None if not
        """
        attr_id = len(self.client.attribute_records)
        new_attribute = Attribute(self.client, attr_id, name, value, self)
        # Add attribute to main list, and then to task.
        attr_response = self.client.connection.post(f"attributes", {"id": attr_id, "name": name})
        task_response = self.client.connection.post(f"tasks/{self.id}/attributes", {"id": attr_id, "name": name, "value": value})

        if task_response["code"] == 200 and attr_response["code"] == 200:
            self.attributes.append(new_attribute)
            # Add label to task detail view
            new_attribute.label.grid(row=self.detail_view["attr_row"], column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            self.detail_view["attr_row"] += 1
            # Add to current options
            self.attribute_options["current_options"].append(new_attribute.option)
            new_attribute.option["frame"].grid(row=self.attribute_options["current_row"], column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            self.attribute_options["current_row"] += 1
            # Clear the add attribute textboxes
            self.attribute_options["new_name"].delete("1.0", "end")
            self.attribute_options["new_value"].delete("1.0", "end")

            self.log.info(f"Attribute created and added to task {self.id}: {new_attribute}")
            return new_attribute
        else:
            self.log.error(f"Adding attribute to list gave: {attr_response["code"]} : {attr_response["message"]}")
            self.log.error(f"Adding attribute to task gave: {task_response["code"]} : {task_response["message"]}")
            return None

    def add_attribute(self, attr_id: int, value: str) -> Attribute | None:
        """Add an existing attribute to the task, and update options.
        :param attr_id: ID of the attribute to be added
        :param value: New value for the attribute
        :return: Newly added attribute
        """
        ids = [attr.id for attr in self.attributes]
        if attr_id in ids:
            self.log.warning(f"Attribute {attr_id} already exists in task {self.id}")
            return None
        name = self.client.attribute_records[attr_id].name
        response = self.client.connection.post(f"tasks/{self.id}/attributes", {"id": attr_id, "name": name, "value": value})
        if response["code"] == 200:
            # Create new attribute
            new_attribute = Attribute(self.client, attr_id, name, value, self)
            self.attributes.append(new_attribute)

            # Add to current options
            new_attribute.option["frame"].grid(row=self.attribute_options["current_row"], column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            self.attribute_options["current_row"] += 1
            self.attribute_options["current_options"].append({attr_id: new_attribute.option})

            # Get existing option based off of key in dict
            existing_option = next((opt for opt in self.attribute_options["existing_options"] if list(opt.keys())[0] == attr_id), None)
            if existing_option is not None:
                # Remove from existing options so it can't be duplicated
                self.attribute_options["existing_options"].remove(existing_option)
                existing_option[attr_id]["frame"].destroy()



            # Add attribute to task detail view
            new_attribute.label.grid(row=self.detail_view["attr_row"], column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
            self.detail_view["attr_row"] += 1
            self.log.info(f"Attribute added to task {self.id}: {new_attribute}")

            return new_attribute
        else:
            print(f"Error adding attribute: {response["code"]} : {response["message"]}")
            return None

    def remove_attribute(self, attr_id: int) -> bool:
        """Remove attribute from task, and delete it from memory. Update options as well.
        :param attr_id: ID of the attribute to be removed
        :return: True if successful, False if not
        """
        # Get attribute based on list of attributes
        attribute = next((attr for attr in self.attributes if attr.id == attr_id), None)
        print(attribute.id)
        attr_id = attribute.id
        response = self.client.connection.delete(f"tasks/{self.id}/attributes", {"id": attribute.id})
        if response["code"] == 200:
            # Remove attribute from task
            attribute.label.grid_forget()
            self.attributes.remove(attribute)
            self.attribute_options["current_options"].remove({attribute.id: attribute.option})
            # Fix the attribute options
            attribute.option["frame"].destroy()

            # Finally, get rid of attribute
            removed = attribute.remove()

            # Add back a record option
            record = self.client.attribute_records[attr_id]
            record.build_record_option(self.options_frame, self)
            self.attribute_options["existing_row"] += 1
            record.record["frame"].grid(row=self.attribute_options["existing_row"], column=0, columnspan=3, sticky="nsw", pady=10, padx=10)

            # Add back to existing options, so it can be picked again
            self.attribute_options["existing_options"].append({attr_id: record.record})

            if removed:
                self.log.info(f"Attribute removed from task {self.id}: {attribute}")
                del attribute
                return True
            else:
                self.log.error(f"Error removing attribute from task {self.id}: {attribute}")
        else:
            self.log.error(f"Error removing attribute from task: {response["code"]} : {response["message"]}")
            return False

    def update_attribute(self, attr_id, value):
        """Update attribute value
        :param attr_id: ID of the attribute to be updated
        :param value: New value for the attribute
        """
        # Get attribute
        attribute = self.attributes[attr_id]

        # Update the attribute
        updated = attribute.edit(value)

        if updated is not None:
            self.attribute_options["current_options"][attr_id] = updated.option
            self.log.info(f"Attribute updated in task {self.id}: {attribute}")
        else:
            self.log.error(f"Error updating attribute in task {self.id}: {attribute}")


# Scrolling events
def scroll(event, widget):
    y_steps = 5
    if event.num == 4:
        y_steps *= -1
    widget.yview_scroll(y_steps, "units")


def final_scroll(event, widget, func):
    # Apparently tkinter uses events for Windows and Linux...
    # For windows, to be able to scroll you would just set one, and have it be <MouseWheel>
    widget.bind_all("<Button-4>", func)
    widget.bind_all("<Button-5>", func)


def stop_scroll(event, widget):
    widget.bind_all("<Button-4>")
    widget.bind_all("<Button-5>")


class Client(LoggingHandler):
    """TODO CLIENT DOCSTRING"""

    def __init__(self, connection, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = self.build_root(ctk.CTk())
        self.connection: Connection = connection
        self.tasks: list[Task] = []
        self.attribute_records: list[AttributeRecord] = []
        self.menu_bar = self.build_menu(),
        self.task_container = self.build_task_list_container()
        self.extra_space, self.detail_container = self.build_detail_container()
        self.help_page = None
        self.log.info("Client created")
        self.build_initial_ui()

    # Build default UI
    def build_initial_ui(self):
        """Build the initial UI for the application"""
        # tkLayout
        #  root
        #  > menu_bar [[menu_bar]]
        #  > task_container [[task_container]]
        #  > detail_container [[detail_container]]
        self.fetch_attributes()
        self.fetch_tasks()
        self.build_task_list()
        self.build_task_details()
        self.help_page = self.build_help_page()
        self.log.info("Initial UI built")
        self.root.update()
        self.root.mainloop()

    def build_menu(self):
        """Create the menu bar and buttons on it.
        :return: tk Object for menu bar and all buttons.
        """
        # tkLayout #[[menu_bar]]
        #  menu_bar
        #  > sorting_button
        #  > add_task_button
        #  > help_button
        # Add menu
        menu_bar = ctk.CTkFrame(self.root)
        menu_bar.grid(row=0, column=0, columnspan=4, sticky='nsew')

        # Sort & Filter
        sorting_button = ctk.CTkButton(menu_bar, text="Sort and Filter", font=("Arial", 20), width=40, height=20)
        sorting_button.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)

        # Add
        add_task_button = ctk.CTkButton(menu_bar, text="Add Task", font=("Arial", 20), width=20, height=20,
                                        command=self.add_task)
        add_task_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)

        # Help Button
        help_button = ctk.CTkButton(menu_bar, text="What's New? / Help", font=("Arial", 20), width=20, height=20,
                                    command=self.toggle_help)
        help_button.grid(row=0, column=4, sticky="nsew", pady=10, padx=10)

        # Config menu bar grid
        menu_bar.columnconfigure(0, weight=1)
        menu_bar.columnconfigure(1, weight=1)
        menu_bar.columnconfigure(2, weight=4)
        menu_bar.columnconfigure(3, weight=4)
        menu_bar.columnconfigure(4, weight=1)

        return {
            "menu_bar": menu_bar,
            "sort": sorting_button,
            "add": add_task_button,
            "help": help_button
        }

    def build_root(self, root: ctk.CTk):
        """Build the root window for the application"""
        root.configure(background="gray14")
        root.geometry('1200x800')
        # Adding columns and rows
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=50)
        root.rowconfigure(0, weight=1)
        root.rowconfigure(1, weight=20)
        return root

    def build_task_list_container(self):
        """Build a scrollable container for the task list
        :return: The container for the task list
        """
        # tkLayout
        #  task_container #[[task_container]]
        #  > left_canvas
        #    > task_list_container
        #      > button[] [[button]]
        #  > left_scrollbar

        task_container = ctk.CTkFrame(self.root)
        task_container.grid(row=1, column=0, sticky='nsew')
        task_container.columnconfigure(0, weight=1)
        task_container.rowconfigure(0, weight=1)

        # Create a canvas so that it can be scrollable
        left_canvas = ctk.CTkCanvas(task_container, bg="gray14", highlightthickness=0)
        left_canvas.grid(row=0, column=0, sticky='nsew')

        left_scrollbar = ctk.CTkScrollbar(task_container, orientation='vertical', command=left_canvas.yview)
        left_scrollbar.grid(row=0, column=1, sticky='nsew')

        left_canvas['yscrollcommand'] = left_scrollbar.set
        left_canvas['yscrollincrement'] = 7
        left_canvas.columnconfigure(0, weight=1)
        left_canvas.rowconfigure(0, weight=1)

        task_list_container = ctk.CTkFrame(left_canvas)
        left_canvas.create_window((0, 0), window=task_list_container, anchor='nw', tags='expand1')
        task_list_container.columnconfigure(0, weight=1)

        left_canvas.bind('<Configure>', lambda event: left_canvas.itemconfigure('expand1', width=event.width))
        task_list_container.update_idletasks()
        left_canvas.config(scrollregion=left_canvas.bbox('all'))

        def update_scrollregion_left(event):
            left_canvas.configure(scrollregion=left_canvas.bbox('all'))

        task_list_container.bind('<Configure>', update_scrollregion_left)

        left_canvas.bind("<Enter>",
                         lambda event: final_scroll(event, left_canvas, lambda event: scroll(event, left_canvas)))
        left_canvas.bind("<Leave>", lambda event: stop_scroll(event, left_canvas))
        self.log.debug(f"Task list container built: {task_container}")
        return task_list_container

    def build_detail_container(self):
        """Build a scrollable container for the task details
        :return: The container for the task details
        """
        # tkLayout
        #  detail_container #[[detail_container]]
        #  > right_canvas
        #    > task_detail_container
        #      > task_detail_frame[] [[task_detail_frame]]
        #  > right_scrollbar
        detail_container = ctk.CTkFrame(self.root, bg_color="gray14", fg_color="gray14")
        detail_container.grid(row=1, column=1, sticky='nsew')
        detail_container.columnconfigure(0, weight=1)
        detail_container.rowconfigure(0, weight=1)

        # Create a canvas so that it can be scrollable
        right_canvas = ctk.CTkCanvas(detail_container, bg="gray14", highlightthickness=0)
        right_canvas.grid(row=0, column=0, sticky='nsew')

        right_scrollbar = ctk.CTkScrollbar(detail_container, orientation='vertical', command=right_canvas.yview)
        right_scrollbar.grid(row=0, column=1, sticky='nsew')

        right_canvas['yscrollcommand'] = right_scrollbar.set
        right_canvas['yscrollincrement'] = 7
        right_canvas.columnconfigure(0, weight=1)
        right_canvas.rowconfigure(0, weight=1)

        task_detail_container = ctk.CTkFrame(right_canvas)
        right_canvas.create_window((0, 0), window=task_detail_container, anchor='nw', tags='expand')
        task_detail_container.columnconfigure(0, weight=1)

        def update_scrollregion_right(event):
            right_canvas.configure(scrollregion=right_canvas.bbox('all'))

        task_detail_container.bind('<Configure>', update_scrollregion_right)

        right_canvas.bind('<Configure>', lambda event: right_canvas.itemconfigure('expand', width=event.width))
        task_detail_container.update_idletasks()
        right_canvas.config(scrollregion=right_canvas.bbox('all'))

        right_canvas.bind("<Enter>",
                          lambda event: final_scroll(event, right_canvas, lambda event: scroll(event, right_canvas)))
        right_canvas.bind("<Leave>", lambda event: stop_scroll(event, right_canvas))
        self.log.debug(f"Detail container built: {detail_container}")

        extra_space = ctk.CTkLabel(task_detail_container, text="", bg_color="gray14", fg_color="gray14", height=500)
        extra_space.grid(row=0, rowspan=3, column=0, columnspan=4, sticky="nsew")

        return extra_space, task_detail_container

    def build_help_page(self) -> ctk.CTkFrame:
        """Build the help page for the application. It has two parts, one for new features, and one for help."""
        # Move text to file
        help_page = ctk.CTkFrame(self.detail_container, bg_color="gray14", fg_color="gray14")
        help_page.grid(row=1, column=0, columnspan=4, sticky='nsew')
        help_page.columnconfigure(0, weight=1)
        help_page.rowconfigure(0, weight=1)
        help_page.rowconfigure(1, weight=2)
        help_page.rowconfigure(2, weight=1)
        help_page.rowconfigure(3, weight=2)

        #TODO: Update New Content
        info_text = '''View
        - You are now able to view all of your tasks on the main page, 
          and you can click on a task to show more of its details
        Add
        - You are now able to add more tasks, from a button on the main page.
        - When adding a task, the parts you need to fill out are highlighted in blue.
        - If you want, you can add attributes to your tasks to better categorize them.
        Edit
        - You are now able to edit tasks, and change change any of the details that 
          you added originally, like attributes, or the date.'''

        help_text = '''Viewing
        - To view a task, click on the task in the list on the left.
        - The task details will appear on the right.
        - If you want to see more tasks, you can scroll through the list on the left.
        Adding
        - To add a task, click the "Add Task" button on the main page.
        - Fill out the name, date, and description of the task.
        - If you want, you can add attributes to your task to better categorize it.
        - Attributes can be things like "Urgency", "Importance", or "Type".
        - To add an attribute, click the "Attributes" button on the task detail view.
        - You can add new attributes, or existing ones in other tasks.
        Editing
        - To edit a task, click the "Edit" button on the task detail view.
        - You can change the name, date, description, and attributes of the task.
        - To edit an attribute, click the "Attributes" button on the task detail view.
        - You can change the value of the attribute.
        - To remove an attribute, click the "Remove" button next to the attribute.
        - To add an attribute, click the "Add" button next to the attribute, 
          which can be an existing one, or brand new.
        - To save your changes, click the "Save" button on the task detail view.
        '''

        # New Info
        new_title = ctk.CTkLabel(help_page, text="What's New?", font=("Arial", 30), bg_color="gray14",
                                 fg_color="gray14",
                                 height=2)
        new_title.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
        new_info = ctk.CTkTextbox(help_page, font=("Arial", 20), bg_color="gray14", fg_color="gray14",
                                  width=800, spacing1=10, height=400, activate_scrollbars=False)
        new_info.insert('1.0', info_text)
        new_info.configure(state="disabled")
        new_info.grid(row=1, column=0, sticky="nsw", padx=10)
        # Help
        help_title = ctk.CTkLabel(help_page, text="Help", font=("Arial", 30), bg_color="gray14", fg_color="gray14",
                                  height=2)
        help_title.grid(row=2, column=0, sticky="nsw", padx=10, pady=10)
        help_info = ctk.CTkTextbox(help_page, font=("Arial", 20), bg_color="gray14", fg_color="gray14",
                                   width=800, spacing1=10, height=1000, activate_scrollbars=False, wrap="word")
        help_info.insert('1.0', help_text)
        help_info.configure(state="disabled")
        help_info.grid(row=3, column=0, sticky="nsw", padx=10)
        self.log.debug(f"Help page built: {help_page}")
        return help_page

    def build_task_list(self):
        """Build the task list on the left side of the screen"""
        open_tasks = [task for task in self.tasks if task.status == "open"]
        closed_tasks = [task for task in self.tasks if task.status == "closed"]

        tasks = open_tasks + closed_tasks
        for i, task in enumerate(tasks):
            task.list_item["button"].grid(row=i, column=0, sticky="nsw", pady=10, padx=10)
            self.task_container.rowconfigure(i, weight=1, uniform="row")
        self.log.info(f"Built {len(self.tasks)} tasks in task list")

    def build_task_details(self):
        """Grid all the task details on the right side of the screen"""
        for task in self.tasks:
            task.detail_view["frame"].grid(row=1, column=1, columnspan=3, sticky='new')
            self.detail_container.rowconfigure(0, weight=1, uniform="row")
        self.log.info(f"Built {len(self.tasks)} task details")

    def toggle_attribute_options(self, n):
        """Toggle the attribute options for task n
        :param n: Task to toggle
        """
        task = self.tasks[n]
        if task.options_open is True:
            task.options_open = False
            task.detail_view["edit"].configure(state="normal")
            # Hide the attribute options
            task.attribute_options["frame"].grid_forget()
            # Edit all attributes from temp storage
            for i, attr in enumerate(task.attributes):
                attr.edit(attr.value)
        else:
            task.options_open = True
            # Disable closing editor so that it won't be saved while open
            task.detail_view["edit"].configure(state="disabled")
            # Show the attribute options
            task.attribute_options["frame"].grid(row=3, column=0, columnspan=3, rowspan=3, sticky="nsw")
            task.attribute_options["frame"].tkraise()

    # Updating Data
    def fetch_tasks(self):
        """Fetch all tasks from the server
        :return: True if successful, False if not
        """
        response = self.connection.get("tasks/all")
        if response["code"] == 200:
            for task in response["data"]:
                attr_list = []
                for attr in task["attributes"]:
                    attr_list.append(Attribute(self, attr["id"], attr["name"], attr["value"]))
                new_task = Task(self, task["id"], task["name"], task["date"], attr_list, task["description"], task["status"])
                new_task.assign_attributes()
                self.tasks.append(new_task)

            self.log.info(f"Fetched {len(self.tasks)} tasks from server")
            return True
        else:
            self.log.error(f"Error fetching tasks: {response["code"]} : {response["message"]}")
            return False

    def fetch_attributes(self) -> bool:
        """Fetch all attributes from the server
        :return: True if successful, False if not
        """
        response = self.connection.get("attributes/all")
        if response["code"] == 200:
            for attr in response["data"]:
                new_attribute = AttributeRecord(self, attr["id"], attr["name"])
                self.attribute_records.append(new_attribute)
            self.log.info(f"Fetched {len(self.attribute_records)} attribute records from server")
            return True
        else:
            self.log.error(f"Error fetching attributes: {response["code"]} : {response["message"]}")
            return False

    def add_task(self):
        """TODO:Add new task to the server and UI"""
        new_task = Task(self, len(self.tasks), "New Task", "2024-01-01", [], "Description", "open")
        response = self.connection.post("tasks/all", {"id": len(self.tasks), "name": "New Task", "date": "2024-01-01", "attributes":[], "description": "Description", "status": "open"})
        if response["code"] != 200:
            self.log.error(f"Error adding new task: {response["code"]} : {response["message"]}")
            return
        self.tasks.append(new_task)
        new_task.assign_attributes()
        self.build_task_list()
        self.build_task_details()
        self.log.info(f"Added new task {new_task}")
        self.change_task(len(self.tasks) - 1)
        self.edit_task(len(self.tasks) - 1)

    def edit_task(self, n):
        """Edit task n. Toggle editing on and off
        :param n: Task to edit
        """
        task = self.tasks[n]
        if task.editing is True:
            task.editing = False
            task.detail_view["name"].configure(state="disabled", fg_color="gray14")
            task.detail_view["date"].configure(state="disabled", fg_color="gray20")
            task.detail_view["description"].configure(state="disabled", fg_color="gray12")
            task.detail_view["attributes"].configure(state="disabled", fg_color="gray14")
            task.detail_view["frame"].configure(bg_color="gray14", fg_color="gray14")
            task.detail_view["frame"].grid(row=1, column=1, columnspan=3, sticky='new')
            task.detail_view["edit"].configure(text="Edit")
            self.log.debug(f"Task {n} editing toggled off")
            data = {
                    "id": n,
                    "name": task.detail_view["name"].get("1.0", "end-1c"),
                    "date": task.detail_view["date"].get("1.0", "end-1c"),
                    "description": task.detail_view["description"].get("1.0", "end-1c"),
                    "status": "closed" if task.detail_view["complete"].get() else "open"
            }
            task.edit(data)
            task.name = data["name"]
            task.date = data["date"]
            task.description = data["description"]
            task.status = data["status"]
            self.log.debug(f"Sent data {data} to server for task {n}")
            self.log.info(f"Task {n} updated")
        else:
            task.editing = True
            task.detail_view["edit"].configure(state="normal")
            task.detail_view["name"].configure(state="normal", fg_color="royal blue")
            task.detail_view["name"].focus_set()
            task.detail_view["date"].configure(state="normal", fg_color="royal blue")
            task.detail_view["description"].configure(state="normal", fg_color="royal blue")
            task.detail_view["attributes"].configure(state="normal", fg_color="royal blue")
            task.detail_view["frame"].configure(bg_color="gray20", fg_color="gray20")
            task.detail_view["frame"].grid(row=1, column=1, columnspan=3, sticky='new')
            task.detail_view["edit"].configure(text="Save")

    def delete_task(self, n):
        """TODO:Delete task from server and UI"""
        pass

    def toggle_active(self, n: int):
        """Toggle the active status of a task. Change checkmark and colors, and task status
        :param n: Task to toggle
        :return: True if successful, False if not
        """
        #
        task = self.tasks[n]
        task.toggle_active()
        if task.status == "open":
            task.list_item["button"].configure(fg_color="#1F6AA5")
            task.list_item["filler"].configure(text="", font=("Arial", 20), fg_color="#1F6AA5")
            task.list_item["name"].configure(fg_color="#1F6AA5")
            task.list_item["attributes"].configure(fg_color="#1F6AA5")
        else:
            task.list_item["button"].configure(bg_color="gray14", fg_color="gray20")
            task.list_item["filler"].configure(text="✓", font=("Arial", 20), bg_color="gray20", fg_color="gray20")
            task.list_item["name"].configure(bg_color="gray20", fg_color="gray20")
            task.list_item["attributes"].configure(bg_color="gray20", fg_color="gray20")
        # Rebuild list
        self.build_task_list()
        self.log.info(f"Task {n} toggled to {task.status}")

    def change_task(self, n: int):
        """Change the task that is being viewed
        :param n: ID of the task to be viewed
        """
        if self.help_page.winfo_ismapped():
            self.help_page.grid_forget()
        self.extra_space.tkraise()
        self.tasks[n].detail_view["frame"].tkraise()

    def toggle_help(self):
        """TODO:Toggle help page"""
        if self.help_page.winfo_ismapped():
            self.help_page.grid_forget()
        else:
            self.help_page.grid(row=1, column=0, columnspan=4, sticky='nsew')
            self.help_page.tkraise()

    def add_attribute(self, n, name, value):
        """TODO:Add attribute to task n"""
        pass

    def remove_attribute(self, n, index):
        """TODO:Remove attribute from task n"""
        pass

    def update_attribute(self, n, name, value):
        """TODO:Update attribute in task n"""
        pass


class Connection(LoggingHandler):
    """The ZMQ Socket Connection to the server"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:5555")

    def get(self, path: str) -> dict:
        """Get data from server
        :param path: The path to the data to be accessed. Format will be [tasks|attributes]/[all|id]
        :return: Response from server
        """
        return self.request("get", path)

    def post(self, path: str, data: dict) -> dict:
        """Add data to server
        :param path: The path to the data to be added. Format will be [tasks|attributes]
        :param data: The data to be added. Will include the new data for the task or attribute
        :return: Response from server
        """
        return self.request("post", path, data)

    def put(self, path: str, data: dict) -> dict:
        """Update data on server
        :param path: The path to the data to be updated. Format will be [tasks|attributes]/[id]
        :param data: The data to be updated. Will include the new data for the task or attribute
        :return: Response from server
        """
        return self.request("put", path, data)

    def delete(self, path: str, data) -> dict:
        """Delete data from server
        :param path: The path to the data to be deleted. Format will be [tasks|attributes]/[id]
        :param data: The data to be deleted. Will be empty for most delete requests
        :return: Response from server
        """
        return self.request("delete", path, data)

    def request(self, action: str, path: str, data: dict = None) -> dict:
        """Send a request to server and return response
        :param action: The type of request to be made. Can be "get", "post", "put", or "delete"
        :param path: The path to the data to be accessed. Format will be [tasks|attributes]/[all|id]
        :param data: The data to be sent to the server. Will be empty for get and delete requests
        :return: The response from the server. Will include the data and a status code
        """
        payload = {
            "type": action,
            "path": path,
            "data": data
        }

        self.socket.send_string(json.dumps(payload))
        response = json.loads(self.socket.recv_string())
        print(f"Action {action} to {path} gave response: {response}")

        return response


# REMOVE
c = Client(Connection())
# t = Task(c, 1, "Task 1", "2021-12-31", "This is a task", [], "open")
# attrib = Attribute(c, 1, "Attribute 1", "Value 1", t)
# t.attributes.append(attrib)
# print(t)
# print(task.attributes)
# attribute.remove()
# print(task.attributes)

context = zmq.Context()
print("Connecting to task server…")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

# UI Setup and Shape
# root = ctk.CTk()
# root.configure(background="gray14")
# root.geometry('1200x800')
# # Adding columns and rows
# root.columnconfigure(0, weight=1)
# root.columnconfigure(1, weight=50)
# root.rowconfigure(0, weight=1)
# root.rowconfigure(1, weight=20)

# Add container for tasks in left column
# task_container = ctk.CTkFrame(root)
# task_container.grid(row=1, column=0, sticky='nsew')
# task_container.columnconfigure(0, weight=1)
# task_container.rowconfigure(0, weight=1)
# # Create a canvas that can be scrollable
# left_canvas = ctk.CTkCanvas(task_container, bg="gray14", highlightthickness=0)
# left_canvas.grid(row=0, column=0, sticky='nsew')
# left_scrollbar = ctk.CTkScrollbar(task_container, orientation='vertical', command=left_canvas.yview)
# left_scrollbar.grid(row=0, column=1, sticky='nsew')
# left_canvas['yscrollcommand'] = left_scrollbar.set
# left_canvas['yscrollincrement'] = 30
# left_canvas.columnconfigure(0, weight=1)
# left_canvas.rowconfigure(0, weight=1)
# left_final_window = ctk.CTkFrame(left_canvas)
# left_canvas.create_window((0, 0), window=left_final_window, anchor='nw', tags='expand1')
# left_final_window.columnconfigure(0, weight=1)
#
# left_canvas.bind('<Configure>', lambda event: left_canvas.itemconfigure('expand1', width=event.width))
# left_final_window.update_idletasks()
# left_canvas.config(scrollregion=left_canvas.bbox('all'))
#
#
# def update_scrollregion_left(event):
#     left_canvas.configure(scrollregion=left_canvas.bbox('all'))
#
#
# left_final_window.bind('<Configure>', update_scrollregion_left)

# Add ability to scroll


# Creating details panel
# right_container = ctk.CTkFrame(root, bg_color="gray14", fg_color="gray14")
# right_container.grid(row=1, column=1, sticky='nsew')
# right_container.columnconfigure(0, weight=1)
# right_container.rowconfigure(0, weight=1)
#
# right_canvas = ctk.CTkCanvas(right_container, bg="gray14", highlightthickness=0)
# right_canvas.grid(row=0, column=0, sticky='nsew')
#
# right_scrollbar = ctk.CTkScrollbar(right_container, orientation='vertical', command=right_canvas.yview)
# right_scrollbar.grid(row=0, column=1, sticky='nsew')
# right_canvas['yscrollcommand'] = right_scrollbar.set
# right_canvas['yscrollincrement'] = 30
# right_canvas.columnconfigure(0, weight=1)
# right_canvas.rowconfigure(0, weight=1)
# right_final_window = ctk.CTkFrame(right_canvas)
# right_canvas.create_window((0, 0), window=right_final_window, anchor='nw', tags='expand')
# right_final_window.columnconfigure(0, weight=1)
#
# right_canvas.bind('<Configure>', lambda event: right_canvas.itemconfigure('expand', width=event.width))
# right_final_window.update_idletasks()
# right_canvas.config(scrollregion=right_canvas.bbox('all'))


# def update_scrollregion_right(event):
#     right_canvas.configure(scrollregion=right_canvas.bbox('all'))
#
#
# right_final_window.bind('<Configure>', update_scrollregion_right)


# def scroll(event, widget):
#     widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
#
#
# def final_scroll(event, widget, func):
#     widget.bind_all("<MouseWheel>", func)
#
#
# def stop_scroll(event, widget):
#     widget.unbind_all("<MouseWheel>")


# Make sure scrolling happens in the right place
# left_canvas.bind("<Enter>", lambda event: final_scroll(event, left_canvas, lambda event: scroll(event, left_canvas)))
# left_canvas.bind("<Leave>", lambda event: stop_scroll(event, left_canvas))
#
# right_canvas.bind("<Enter>", lambda event: final_scroll(event, right_canvas, lambda event: scroll(event, right_canvas)))
# right_canvas.bind("<Leave>", lambda event: stop_scroll(event, right_canvas))


# def fetch_tasks():
#     # Get Tasks
#     payload = {
#         "type": "get",
#         "path": "tasks/all",
#         "data": ""
#     }
#     socket.send_string(json.dumps(payload))
#
#     response = json.loads(socket.recv_string())
#     print(f"Fetching tasks gave response: {response}")
#
#     if response["response"] == 400:
#         print("Server Error")
#         tasks = []
#     else:
#         tasks = response["response"]
#     return tasks
#
#
# def fetch_attributes():
#     payload = {
#         "type": "get",
#         "path": "attributes/all",
#         "data": ""
#     }
#     socket.send_string(json.dumps(payload))
#
#     response = json.loads(socket.recv_string())
#     print(f"Fetching attributes gave response: {response}")
#
#     if response["response"] == 400:
#         print("Server Error")
#         attributes = []
#     else:
#         attributes = response["response"]
#     return attributes


# tasks = fetch_tasks()
# attribute_list = fetch_attributes()

# Help Page
# help_page = ctk.CTkFrame(right_final_window, bg_color="gray14", fg_color="gray14")
# help_page.grid(row=1, column=0, columnspan=4, sticky='nsew')
# help_page.columnconfigure(0, weight=1)
# help_page.rowconfigure(0, weight=1)
# help_page.rowconfigure(1, weight=2)
# help_page.rowconfigure(2, weight=1)
# help_page.rowconfigure(3, weight=2)
#
# info_text = '''View
# - You are now able to view all of your tasks on the main page,
#   and you can click on a task to show more of its details
# Add
# - You are now able to add more tasks, from a button on the main page.
# - When adding a task, the parts you need to fill out are highlighted in blue.
# - If you want, you can add attributes to your tasks to better categorize them.
# Edit
# - You are now able to edit tasks, and change change any of the details that
#   you added originally, like attributes, or the date.'''
#
# help_text = '''Viewing
# - To view a task, click on the task in the list on the left.
# - The task details will appear on the right.
# - If you want to see more tasks, you can scroll through the list on the left.
# Adding
# - To add a task, click the "Add Task" button on the main page.
# - Fill out the name, date, and description of the task.
# - If you want, you can add attributes to your task to better categorize it.
# - Attributes can be things like "Urgency", "Importance", or "Type".
# - To add an attribute, click the "Attributes" button on the task detail view.
# - You can add new attributes, or existing ones in other tasks.
# Editing
# - To edit a task, click the "Edit" button on the task detail view.
# - You can change the name, date, description, and attributes of the task.
# - To edit an attribute, click the "Attributes" button on the task detail view.
# - You can change the value of the attribute.
# - To remove an attribute, click the "Remove" button next to the attribute.
# - To add an attribute, click the "Add" button next to the attribute, which can be an existing one, or brand new.
# - To save your changes, click the "Save" button on the task detail view.
# '''
#
# # New Info
# new_title = ctk.CTkLabel(help_page, text="What's New?", font=("Arial", 30), bg_color="gray14", fg_color="gray14",
#                          height=2)
# new_title.grid(row=0, column=0, sticky="nsw", padx=10, pady=10)
# new_info = ctk.CTkTextbox(help_page, font=("Arial", 20), bg_color="gray14", fg_color="gray14",
#                           width=700, spacing1=10, height=400, activate_scrollbars=False)
# new_info.insert('1.0', info_text)
# new_info.configure(state="disabled")
# new_info.grid(row=1, column=0, sticky="nsw", padx=10)
# # Help
# help_title = ctk.CTkLabel(help_page, text="Help", font=("Arial", 30), bg_color="gray14", fg_color="gray14", height=2)
# help_title.grid(row=2, column=0, sticky="nsw", padx=10, pady=10)
# help_info = ctk.CTkTextbox(help_page, font=("Arial", 20), bg_color="gray14", fg_color="gray14",
#                            width=700, spacing1=10, height=1000, activate_scrollbars=False)
# help_info.insert('1.0', help_text)
# help_info.configure(state="disabled")
# help_info.grid(row=3, column=0, sticky="nsw", padx=10)

# Create a dictionary to store the state of each textbox

textbox_states = {}


# def edit_task(n):
#     name, date, description, attributes, attribute_label, complete, edit_button = task_detail_frames[n][1].values()
#     # If the textbox is not in the dictionary, assume it is disabled
#     if textbox_states.get(name, "disabled") == "normal":
#         payload = {
#             "type": "put",
#             "path": f"tasks/{n + 1}",
#             "data": {
#                 "id": n + 1,
#                 "name": name.get("1.0", "end-1c"),
#                 "date": date.get("1.0", "end-1c"),
#                 "description": description.get("1.0", "end-1c"),
#                 "attributes": tasks[n]["attributes"],
#                 "status": "closed" if complete.get() else "open"
#             }
#         }
#         socket.send_string(json.dumps(payload))
#         response = json.loads(socket.recv_string())
#         print(f"Editing task {n + 1} gave response: {response}")
#         for task_detail in task_detail_frames:
#             task_detail[0].destroy()
#         task_detail_frames.clear()
#         build_task_details()
#         build_task_list()
#         change_task(n)
#     else:
#         name.configure(state="normal", fg_color="royal blue")
#         name.focus_set()
#         date.configure(state="normal", fg_color="royal blue")
#         description.configure(state="normal", fg_color="royal blue")
#         attribute_label.configure(state="normal", fg_color="royal blue")
#         # Update the states in the dictionary
#         textbox_states[name] = "normal"
#         textbox_states[date] = "normal"
#         textbox_states[description] = "normal"
#         edit_button.configure(text="Save")


# attribute_options = [None for _ in range(1000)]
#
#
# def build_attribute_options(n):
#     name, date, description, attributes, attribute_label, complete, edit_button = task_detail_frames[n][1].values()
#     print("Building attribute options", tasks[n]["attributes"], n)
#     if attribute_options[n] is not None:
#         # Close Menu
#         for attr in attributes:
#             attr.tkraise()
#         attribute_options[n].destroy()
#         attribute_options[n] = None
#         edit_button.configure(state="normal")
#     else:
#         edit_button.configure(state="disabled")
#         attr_options_frame = ctk.CTkFrame(task_detail_frames[n][0], bg_color="gray14", fg_color="gray14")
#         attribute_options[n] = attr_options_frame
#         attributes = task_detail_frames[n][1]["attributes"]
#         for attr in attributes:
#             attr.lower()
#         attr_options_frame.grid(row=3, column=0, columnspan=3, rowspan=3, sticky="nsw")
#         attr_options_frame.columnconfigure(0, weight=1)
#         attr_options_frame.columnconfigure(1, weight=1)
#         attr_options_frame.columnconfigure(2, weight=1)
#         # Current Attr Label
#         current_attr_label = ctk.CTkLabel(attr_options_frame, text="Current Attributes", font=("Arial", 30), padx=15)
#         current_attr_label.grid(row=0, column=0, sticky="nsw")
#         # Current Attributes
#         max_i = 0
#         for i, attr in enumerate(tasks[n]["attributes"]):
            # attr_frame = ctk.CTkFrame(attr_options_frame, bg_color="gray14", fg_color="gray14")
            # attr_frame.grid(row=i + 1, column=0, columnspan=3, sticky="nsw")
            # attr_frame.columnconfigure(0, weight=1)
            # attr_frame.columnconfigure(1, weight=1)
            # attr_frame.columnconfigure(2, weight=1)
            # attr_name = ctk.CTkLabel(attr_frame, text=f'{attr["name"]}', font=("Arial", 25),
            #                             fg_color="gray20", corner_radius=10, padx=10, pady=10)
            # attr_name.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)
            # attr_value = ctk.CTkTextbox(attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
            #                             fg_color="royal blue", wrap="none")
            # # On Typing, update the attribute
            # attr_value.bind("<KeyRelease>", lambda event, index=i: update_attribute(n, attr["name"] , attr_value.get(
            #     "1.0",
            #                                                                                              "end-1c")))
            # attr_value.insert('1.0', f'{attr["value"]}')
            # attr_value.grid(row=0, column=1, sticky="nsw", pady=10, padx=10)
            # remove_button = ctk.CTkButton(attr_frame, text="Remove", font=("Arial", 25), width=80, bg_color="gray20")
            # remove_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)
            # remove_button.bind("<Button-1>", lambda event, index=i: remove_attribute(n, index))
            # max_i = i

        # Existing Attributes & Label
        # existing_attributes = []
        # for i, attr in enumerate(attribute_list):
        #     if attr["name"] not in [a["name"] for a in tasks[n]["attributes"]]:
        #         existing_attributes.append(attr)
        # if len(existing_attributes) > 0:
        #     existing_attr_label = ctk.CTkLabel(attr_options_frame, text="Existing Attributes", font=("Arial", 30),
        #                                        padx=15)
        #     existing_attr_label.grid(row=max_i + 2, column=0, sticky="nsw")
        #     for i, attr in enumerate(existing_attributes):
                # attr_frame = ctk.CTkFrame(attr_options_frame, bg_color="gray14", fg_color="gray14")
                # attr_frame.grid(row=max_i + i + 3, column=0, columnspan=3, sticky="nsw")
                # attr_frame.columnconfigure(0, weight=1)
                # attr_frame.columnconfigure(1, weight=1)
                # attr_frame.columnconfigure(2, weight=1)
                # attr_name = ctk.CTkTextbox(attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                #                             fg_color="gray20", wrap="none", corner_radius=10,)
                # attr_name.insert('1.0', f'{attr["name"]}')
                # attr_name.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)
                # attr_value = ctk.CTkTextbox(attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
                #                             fg_color="royal blue", wrap="none", corner_radius=10)
                # attr_value.insert('1.0', "value")
                # attr_value.grid(row=0, column=1, sticky="nsw", pady=10, padx=10)
                # add_button = ctk.CTkButton(attr_frame, text="Add", font=("Arial", 25), width=80, bg_color="gray20")
                # add_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)
                # add_button.bind("<Button-1>", lambda event, index=i: add_attribute(n, attr_name.get("1.0", "end-1c"), attr_value.get("1.0", "end-1c")))
#                 max_i = i
#             max_i += 2
#
#         # New Attr Label (Just 2 blank textboxes and a button to add. If one is added, add another)
#         new_attr_label = ctk.CTkLabel(attr_options_frame, text="New Attributes", font=("Arial", 30), padx=15)
#         new_attr_label.grid(row=max_i + 4, column=0, sticky="nsw")
#         new_attr_frame = ctk.CTkFrame(attr_options_frame, bg_color="gray14", fg_color="gray14")
#         new_attr_frame.grid(row=max_i + 5, column=0, columnspan=3, sticky="nsw")
#         new_attr_frame.columnconfigure(0, weight=1)
#         new_attr_frame.columnconfigure(1, weight=1)
#         new_attr_frame.columnconfigure(2, weight=1)
#         new_attr_name = ctk.CTkTextbox(new_attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
#                                        fg_color="royal blue", wrap="none", corner_radius=10)
#         new_attr_name.insert('1.0', "name")
#         new_attr_name.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)
#         new_attr_value = ctk.CTkTextbox(new_attr_frame, font=("Arial", 25), border_width=0, height=1, width=150,
#                                         fg_color="royal blue", wrap="none", corner_radius=10)
#         new_attr_value.insert('1.0', "value")
#         new_attr_value.grid(row=0, column=1, sticky="nsw", pady=10, padx=10)
#         add_button = ctk.CTkButton(new_attr_frame, text="Add", font=("Arial", 25), width=80, bg_color="gray14",
#                                    corner_radius=10)
#         add_button.grid(row=0, column=2, sticky="nsw")
#         add_button.bind("<Button-1>", lambda event: add_attribute(n, new_attr_name.get("1.0", "end-1c"),
#                                                                   new_attr_value.get("1.0", "end-1c")))
#         max_i += 1
#         attr_options_frame.rowconfigure(index=max_i + 5, weight=1, uniform="row")
#         attr_options_frame.grid(row=3, column=0, columnspan=3, rowspan=3, sticky="nsw")
#
#
# def update_attribute(n, name, value):
#     print("Updating attribute")
#     # Get attribute with name
#     for i, attr in enumerate(tasks[n]["attributes"]):
#         if attr["name"] == name:
#             tasks[n]["attributes"][i]["value"] = value
#             payload = {
#                 "type": "put",
#                 "path": f"tasks/{n + 1}",
#                 "data": {
#                     "id": n + 1,
#                     "name": task_detail_frames[n][1]["name"].get("1.0", "end-1c"),
#                     "date": task_detail_frames[n][1]["date"].get("1.0", "end-1c"),
#                     "description": task_detail_frames[n][1]["description"].get("1.0", "end-1c"),
#                     "attributes": tasks[n]["attributes"],
#                     "status": tasks[n]["status"]
#                 }
#             }
#             socket.send_string(json.dumps(payload))
#             response = json.loads(socket.recv_string())
#             print(f"Updating attribute {name} to {value} gave response: {response}")
#             break
#
#
# def add_attribute(n, name, value):
#     tasks[n]["attributes"].append({
#         "name": name,
#         "value": value
#     })
#     attribute_list.append({
#         "name": name
#     })
#     # If attribute not in db, add it
#     if name not in [attr["name"] for attr in attribute_list]:
#         payload = {
#             "type": "post",
#             "path": "attributes/",
#             "data": {
#                 "name": name
#             }
#         }
#         socket.send_string(json.dumps(payload))
#         response = json.loads(socket.recv_string())
#         print(f"Adding attribute {name}, with value {value} gave response: {response}")
#     attribute_options[n].destroy()
#     attribute_options[n] = None
#     build_attribute_options(n)
#
#
# def remove_attribute(n, index):
#     attr_name = tasks[n]["attributes"][index]["name"]
#     tasks[n]["attributes"].pop(index)
#     payload = {
#         "type": "put",
#         "path": f"tasks/{n + 1}",
#         "data": {
#             "id": n + 1,
#             "name": task_detail_frames[n][1]["name"].get("1.0", "end-1c"),
#             "date": task_detail_frames[n][1]["date"].get("1.0", "end-1c"),
#             "description": task_detail_frames[n][1]["description"].get("1.0", "end-1c"),
#             "attributes": tasks[n]["attributes"],
#             "status": tasks[n]["status"]
#         }
#     }
#     socket.send_string(json.dumps(payload))
#     response = json.loads(socket.recv_string())
#     print(f"Removing attribute {attr_name} gave response: {response}")
#     attribute_options[n].destroy()
#     attribute_options[n] = None
#     build_attribute_options(n)
#
#
# Add tasks to right side
#
# task_detail_frames = []

# extra_space = ctk.CTkLabel(right_final_window, text="", bg_color="gray14", fg_color="gray14", height=500)
# extra_space.grid(row=0, rowspan=3, column=0, columnspan=4, sticky="nsew")


# def build_task_details():
#     print("Building Task Details")
#     extra_space.tkraise()
#     for i in range(len(tasks)):
#         # Create a new frame for the task detail view and add it to the list
#         task_detail_frame = ctk.CTkFrame(right_final_window, bg_color="gray14", fg_color="gray14", height=800)
#
#         task_detail_frame.columnconfigure(index=0, weight=1, uniform="column")
#         task_detail_frame.columnconfigure(index=1, weight=1)
#         task_detail_frame.columnconfigure(index=2, weight=1, uniform="column")
#         task_detail_frame.rowconfigure(index=0, weight=1)
#         task_detail_frame.rowconfigure(index=1, weight=1)
#
#         # Name Frame
#         name_frame = ctk.CTkFrame(task_detail_frame, bg_color="gray14", fg_color="gray14")
#         name_frame.grid(row=0, column=0, sticky="nsw")
#         name_frame.columnconfigure(0, weight=1)
#         name_frame.columnconfigure(1, weight=1)
#
#         # Name Label
#         name_label = ctk.CTkLabel(name_frame, text=f'Task {tasks[i]["id"]} - ', font=("Arial", 30))
#
#         # Name Textbox
#         task_name = ctk.CTkTextbox(name_frame, font=("Arial", 30), border_width=0,
#                                    height=1, width=300, fg_color="gray14", wrap="none")
#         task_name.insert('1.0', f'{tasks[i]["name"]}')
#         task_name.configure(state="disabled")
#         task_name.grid(row=0, column=1, sticky="nsw", pady=10)
#
#         name_label.grid(row=0, column=0, sticky="nsw", padx=(10, 0))
#
#         # Completion Checkbox
#         complete_frame = ctk.CTkFrame(task_detail_frame, fg_color="gray14", width=100)
#         complete_text = ctk.CTkLabel(complete_frame, text="Complete ", font=("Arial", 30))
#         task_var = ctk.BooleanVar(value=True if tasks[i]["status"] == "closed" else False)
#         complete_box = ctk.CTkCheckBox(complete_frame, variable=task_var, command=lambda index=i: toggle_active(index),
#                                        text="",
#                                        checkbox_width=30,
#                                        checkbox_height=30)
#         complete_text.grid(column=0, row=0, sticky="nsew", pady=10)
#         complete_box.grid(column=1, row=0, sticky="nsew")
#         complete_frame.grid(column=1, row=0, sticky="nsw", pady=10, padx=10)
#
#         # Editing Button
#         edit_button = ctk.CTkButton(task_detail_frame, text="Edit", command=lambda index=i: edit_task(index),
#                                     font=("Arial", 30), width=80, bg_color="gray20")
#         edit_button.grid(column=2, row=0, sticky="nsw", pady=10)
#
#         # Date
#         date = ctk.CTkTextbox(task_detail_frame, font=("Arial", 30), border_width=0, height=1,
#                               width=175,
#                               fg_color="gray20", wrap="none")
#         date.insert('1.0', tasks[i]["date"])
#         date.configure(state="disabled")
#         date.grid(row=1, column=0, columnspan=3, sticky="nsw", padx=15, pady=10)
#
#         # Attribute Label
#         attribute_label = ctk.CTkButton(task_detail_frame, text="Attributes", font=("Arial", 30), command=lambda
#             index=i: build_attribute_options(index), state="disabled", bg_color="gray14", fg_color="gray14")
#         attribute_label.grid(row=2, column=0, columnspan=3, sticky="nsw", pady=10, padx=15)
#         # Attributes
#         max_j = 0
#         attributes = []
#         for j, attr in enumerate(tasks[i]["attributes"]):
#             # attr_text = f'{attr["name"].strip()}: {attr["value"].strip()}'
#             # attribute = ctk.CTkLabel(task_detail_frame, text=attr_text, font=("Arial", 25),
#             #                                fg_color="gray20", corner_radius=10)
#             # attribute.grid(row=3+j, column=0, columnspan=3, sticky="nsw", pady=10, padx=10)
#             # attributes.append(attribute)
#             task_detail_frame.rowconfigure(index=3 + j, weight=1, uniform="row")
#             max_j = j
#
#         # Description Label
#         description_label = ctk.CTkLabel(task_detail_frame, text="Description", font=("Arial", 30), padx=15)
#         description_label.grid(row=max_j + 4, column=0, columnspan=3, sticky="nsw")
#         # Description
#         description = ctk.CTkTextbox(task_detail_frame, font=("Arial", 20), padx=15, wrap='word', width=800,
#                                      height=300, spacing2=10)
#         description.insert('1.0', tasks[i]["description"])
#         description.configure(state="disabled")
#         description.grid(row=max_j + 5, column=0, columnspan=3, sticky="nsw", padx=15, pady=10)
#
#         # Create a Scrollbar and attach it to the Text widget
#         scrollbar = ctk.CTkScrollbar(task_detail_frame, command=description.yview)
#         scrollbar.grid(row=max_j + 5, column=3, sticky='nsew')
#         description['yscrollcommand'] = scrollbar.set
#
#         task_detail_frame.rowconfigure(index=max_j + 4, weight=1)
#         task_detail_frame.rowconfigure(index=max_j + 5, weight=1)
#
#         task_detail_frame.grid(row=1, column=1, columnspan=3, sticky='new')
#         task_detail_frames.append((task_detail_frame, {
#             "name": task_name,
#             "date": date,
#             "description": description,
#             "attributes": attributes,
#             "attribute_label": attribute_label,
#             "complete": task_var,
#             "edit_button": edit_button
#
#         }))




# def add_task():
#     new_task = {
#         "id": len(tasks) + 1,
#         "name": "New Task Name",
#         "date": "2024/01/01",
#         "description": "New Description",
#         "attributes": [],
#         "status": "open"
#     }
#     tasks.append(new_task)
#     payload = {
#         "type": "post",
#         "path": "tasks/",
#         "data": new_task
#     }
#     socket.send_string(json.dumps(payload))
#     response = json.loads(socket.recv_string())
#     print(f"Add task gave response: {response}")
#     for task_detail in task_detail_frames:
#         task_detail[0].destroy()
#     task_detail_frames.clear()
#     build_task_details()
#     build_task_list()
#     change_task(len(tasks) - 1)
#     edit_task(len(tasks) - 1)


def open_help():
    help_page.tkraise()


def change_task(n):
    # Bring the frame of the selected task detail view to the top
    extra_space.tkraise()
    task_detail_frames[n][0].tkraise()


task_buttons = []


def build_task_list():
    print("Building Task List")
    for button in task_buttons:
        button.destroy()
    task_buttons.clear()
    # Create Tasks on left side
    tasks = fetch_tasks()
    button_queue_disabled = []
    button_queue = []
    # for i in range(len(tasks)):

    # button = ctk.CTkButton(left_final_window, command=lambda index=i: change_task(index), text="", width=400,
    #                        height=100)
    # if tasks[i]["status"] == "closed":
    #     button.configure(bg_color="gray20", fg_color="gray20")
    #     button_queue_disabled.append(button)
    # else:
    #     button_queue.append(button)
    # name = ctk.CTkLabel(button, text=f'{tasks[i]["date"]} - {tasks[i]["name"]}', font=("Arial", 20), padx=10, pady=10,
    #                           fg_color="transparent", bg_color="transparent")
    # name.grid(row=0, column=0, sticky="nsw")
    # name.bind("<Button-1>", lambda event, index=i: change_task(index))  # Bind the click event to the label
    # filler = ctk.CTkLabel(button, text="", padx=10)
    # if tasks[i]["status"] == "closed":
    #     filler.configure(text="✓", font=("Arial", 20))
    # filler.grid(row=1, column=0, sticky="w")
    # attr_list = ", ".join(attr["value"] for attr in tasks[i]["attributes"])
    # attributes = ctk.CTkLabel(button, text=f'{attr_list}', font=("Arial", 20), padx=10, pady=10)
    # attributes.grid(row=2, column=0, sticky="nsw")
    # attributes.bind("<Button-1>", lambda event, index=i: change_task(index))
    # task_buttons.append(button)
    i = 0
    for button in button_queue:
        button.grid(row=i, column=0, sticky="nsew", pady=1)
        i += 1
    for button in button_queue_disabled:
        button.grid(row=i, column=0, sticky="nsew", pady=1)
        i += 1


# build_task_list()
# build_task_details()
# change_task(0)

# # Add menu
# menu_bar = ctk.CTkFrame(root)
# menu_bar.grid(row=0, column=0, columnspan=4, sticky='nsew')
#
# # Sort & Filter
# sorting_button = ctk.CTkButton(menu_bar, text="Sort and Filter", font=("Arial", 20), width=40, height=20)
# sorting_button.grid(row=0, column=0, sticky="nsw", pady=10, padx=10)
#
# # Add
# add_task_button = ctk.CTkButton(menu_bar, text="Add Task", font=("Arial", 20), width=20, height=20, command=add_task)
# add_task_button.grid(row=0, column=2, sticky="nsw", pady=10, padx=10)
#
# # Help Button
# help_button = ctk.CTkButton(menu_bar, text="What's New? / Help", font=("Arial", 20), width=20, height=20,
#                             command=open_help)
# help_button.grid(row=0, column=4, sticky="nsew", pady=10, padx=10)
#
# # Config menu bar grid
# menu_bar.columnconfigure(0, weight=1)
# menu_bar.columnconfigure(1, weight=1)
# menu_bar.columnconfigure(2, weight=4)
# menu_bar.columnconfigure(3, weight=4)
# menu_bar.columnconfigure(4, weight=1)

# root.update()
# root.mainloop()