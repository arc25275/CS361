import tkinter as tk

root = tk.Tk()



text = tk.Canvas(root, background="red")
sb = tk.Scrollbar(root, command=text.yview)
sb.pack(side="right", fill="y")
text.configure(yscrollcommand=sb.set)
y = 0
for i in range(40):
    frame = tk.Frame(width=200)
    label = label1 = tk.Label(master=frame, relief="ridge", text=str(i), width=50, height=10)
    label.pack()
    text.create_window(0, y, anchor='nw', window=frame)
    y += 150
text.configure(state="disabled")

text.pack(side="top", anchor="nw", fill="both")

root.mainloop()
