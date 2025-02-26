from tkinter import *
from utils import *

window = Tk()
activeWindows = getAllWindows()
os = getOS()

window.geometry("380x380")
window.title("Streakr")
window.resizable(False, False)

icon = PhotoImage(file="./assets/icon.png")
window.iconphoto(True, icon)

window.config(background = "#0f1117")

clicked = StringVar()
clicked.set("Select App")

dropdown = OptionMenu( window, clicked, *activeWindows )
dropdown.configure(background='#0f1117')
dropdown.place(relx=0.5, rely=0.5, anchor="c")

window.mainloop()