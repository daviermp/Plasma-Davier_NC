import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports

root = tk.Tk()
root.title("DAVIER NC PLASMA")
root.geometry("900x600")
root.configure(bg="#111")

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True)

tab1 = tk.Frame(nb, bg="#111")
nb.add(tab1, text="CONTROL")

tk.Label(tab1, text="DAVIER NC PLASMA V2.0", font=("Arial",18,"bold"), bg="#111", fg="#00ff00").pack(pady=20)

ports = [p.device for p in serial.tools.list_ports.comports()]
combo = ttk.Combobox(tab1, values=ports)
combo.set("Selecciona puerto COM")
combo.pack()

def conectar():
    tk.Label(tab1, text="Conectado a " + combo.get(), fg="green", bg="#111").pack()

tk.Button(tab1, text="CONECTAR", command=conectar, bg="#00ff00", width=20).pack(pady=10)
tk.Button(tab1, text="INICIAR CORTE", bg="red", fg="white", width=20).pack(pady=10)
tk.Button(tab1, text="PARAR", bg="orange", width=20).pack(pady=5)

root.mainloop()
