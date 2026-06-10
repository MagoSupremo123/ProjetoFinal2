import tkinter as tk

root = tk.Tk()
root.title("Meu Aplicativo")
root.geometry("800x600")

label = tk.Label(root, text="Hello, Tkinter!")
label.pack(pady=20)

root.mainloop()