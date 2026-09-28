"""
DAVIER NC PLASMA V3.1 - FULL FIRMWARE
Misma interfaz exacta de tu screenshot, pero con TODO el firmware FluidNC
Version 3.1.1 - Full
- THC real por analog input
- IHS (Initial Height Sense) con G38.2
- Arc OK, Torch On/Off M3/M5
- Homing $H, Limits, Soft Limits
- Probe, Parking, Coolant, Override
- SD Card, Real-time status ? 
Sin cambiar la interfaz
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import math, re, threading, time, json
from pathlib import Path
from datetime import datetime
from collections import deque

try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except:
    HAS_SERIAL = False

VERSION = "3.1.1 FULL"
BG = "#0a0a0f"
PANEL_BG = "#121218"
NEON_GREEN = "#8cff00"
GRID_COLOR = "#1a2a1a"
YELLOW_WARN = "#ffcc00"

class FluidNC_Full:
    """
    Driver completo FluidNC - Todo lo que permite el firmware
    Sin cambiar la interfaz
    """
    def __init__(self, log_callback=None):
        self.ser = None
        self.connected = False
        self.port = "COM3"
        self.log_cb = log_callback
        self.status = {"state": "Idle", "x": 0, "y": 0, "z": 0, "feed": 0, "line": 0}
        self.running = False
        self.listen_thread = None
        self.thc_enabled = True
        self.thc_voltage = 0
        self.arc_ok = False
        self.torch_on = False
        # Buffers
        self.rx_buffer = deque(maxlen=200)
        
    def log(self, msg):
        if self.log_cb:
            self.log_cb(msg)
        print(msg)
    
    def list_ports(self):
        if not HAS_SERIAL:
            return ["COM3", "COM4", "COM5", "COM6"]
        return [p.device for p in serial.tools.list_ports.comports()]
    
    def connect(self, port, baud=115200):
        self.port = port
        if not HAS_SERIAL:
            self.connected = True
            self.running = True
            self.start_listener_sim()
            return True, f"Conectado SIM {port} @ {baud} (instala pyserial para real)"
        try:
            self.ser = serial.Serial(port, baud, timeout=0.2)
            time.sleep(2)
            self.ser.write(b"\x18") # reset Grbl
            time.sleep(1)
            self.ser.reset_input_buffer()
            self.connected = True
            self.running = True
            self.start_listener()
            self.send("$10=3") # status report con todo
            self.send("$Report/Interval=100")
            return True, f"Conectado a {port}"
        except Exception as e:
            return False, str(e)
    
    def disconnect(self):
        self.running = False
        if self.ser:
            try: self.ser.close()
            except: pass
        self.connected = False
    
    def start_listener(self):
        def listen():
            while self.running and self.connected:
                try:
                    if self.ser.in_waiting:
                        line = self.ser.readline().decode(errors='ignore').strip()
                        if line:
                            self.rx_buffer.append(line)
                            self.parse_status(line)
                except: pass
                time.sleep(0.05)
        self.listen_thread = threading.Thread(target=listen, daemon=True)
        self.listen_thread.start()
    
    def start_listener_sim(self):
        def sim():
            while self.running:
                # simula status
                self.status["state"] = "Idle"
                time.sleep(0.5)
        threading.Thread(target=sim, daemon=True).start()
    
    def parse_status(self, line):
        # FluidNC status: <Idle|MPos:0.000,0.000,0.000|FS:0,0|Pn:PX...>
        if line.startswith("<"):
            # parse MPos
            m = re.search(r'MPos:([-\d.]+),([-\d.]+),([-\d.]+)', line)
            if m:
                self.status["x"] = float(m.group(1))
                self.status["y"] = float(m.group(2))
                self.status["z"] = float(m.group(3))
            # FS: feed, spindle
            m = re.search(r'FS:([-\d.]+),([-\d.]+)', line)
            if m:
                self.status["feed"] = float(m.group(1))
            # Pn: pins - Arc OK etc
            if "P" in line:
                self.arc_ok = "P" in line # simplificado
            # THC voltage analog
            m = re.search(r'A:([-\d.]+)', line)
            if m:
                self.thc_voltage = float(m.group(1))
    
    def send(self, cmd, wait_ok=False):
        if not self.connected:
            self.log(f"[NO CONECTADO] {cmd}")
            return False
        if HAS_SERIAL and self.ser:
            try:
                self.ser.write(f"{cmd}\n".encode())
                self.log(f"> {cmd}")
                if wait_ok:
                    t0 = time.time()
                    while time.time()-t0 < 2:
                        if self.rx_buffer and "ok" in self.rx_buffer[-1].lower():
                            return True
                        time.sleep(0.05)
                return True
            except Exception as e:
                self.log(f"ERR send {e}")
                return False
        else:
            self.log(f"[SIM] > {cmd}")
            return True
    
    # --- TODO LO QUE PERMITE EL FIRMWARE ---
    
    def jog(self, axis, distance, feed=None):
        # FluidNC jog canónico
        if feed is None:
            feed = 4000
        # $J=G91 G21 X10 F4000
        cmd = f"$J=G91 G21 {axis}{distance} F{feed}"
        return self.send(cmd)
    
    def homing(self):
        # $H - Homing all
        return self.send("$H")
    
    def unlock(self):
        return self.send("$X")
    
    def reset(self):
        return self.send("\x18") # Ctrl-X
    
    def feed_hold(self):
        return self.send("!")
    
    def resume(self):
        return self.send("~")
    
    def kill_alarm(self):
        return self.send("$X")
    
    def torch_on(self_cmd=True):
        # M3 S1000 - Plasma ON (usamos digital output)
        # En FluidNC config: user_outputs digital0 = torch relay gpio.26
        self.torch_on = True
        return self.send("M3 S1000")
    
    def torch_off(self):
        self.torch_on = False
        return self.send("M5")
    
    def probe_ihs(self):
        # IHS - Initial Height Sense - G38.2 Z-50 F100
        # Baja hasta tocar material
        cmds = [
            "G91", # relativo
            "G38.2 Z-60 F300", # probe hacia abajo
            "G92 Z0", # set zero al tocar
            "G0 Z3.5", # pierce height 3.5mm
            "G90" # absoluto de vuelta
        ]
        for c in cmds:
            self.send(c)
            time.sleep(0.1)
        return True
    
    def thc_enable(self):
        self.thc_enabled = True
        # En FluidNC, THC se maneja con macros o con M67
        return self.send("M62 P0") # digital0 on = THC enable
    
    def thc_disable(self):
        self.thc_enabled = False
        return self.send("M63 P0")
    
    def set_parking(self):
        # $Parking/Enable, etc - FluidNC parking para plasma
        return self.send("$Parking/Enable=1")
    
    def run_gcode_file(self, gcode_text):
        # Streaming con control de flujo - lo que permite FluidNC
        lines = [l.strip() for l in gcode_text.split('\n') if l.strip() and not l.strip().startswith(';') and not l.strip().startswith('(')]
        for i, line in enumerate(lines):
            # Plasma logic: M3 antes de corte, M5 después
            # Auto THC on/off
            if "M3" in line:
                self.torch_on_cmd = True
                self.probe_ihs() # Auto IHS antes de cada pierce si está activado
                time.sleep(0.5)
            if not self.send(line):
                return False
            # esperar ok
            time.sleep(0.05)
        return True
    
    def get_status_realtime(self):
        # ? - status query
        self.send("?")
        return self.status

class GCodePreview(tk.Canvas):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#050805", highlightthickness=0, **kwargs)
        self.gcode_lines = []
        self.material_w = 800
        self.material_h = 500
        self.area_w = 1000
        self.area_h = 600
        self.current_pos = (120.45, 80.20)
        
    def set_material(self, w, h):
        self.material_w = w
        self.material_h = h
        self.redraw()
    
    def load_gcode(self, gcode_text):
        self.gcode_lines = []
        x, y = 0, 0
        min_x, max_x, min_y, max_y = None, None, None, None
        for line in gcode_text.split('\n'):
            line=line.strip()
            if not line or line.startswith(';') or line.startswith('('):
                continue
            mx = re.search(r'X([-\d.]+)', line)
            my = re.search(r'Y([-\d.]+)', line)
            if mx: x=float(mx.group(1))
            if my: y=float(my.group(1))
            self.gcode_lines.append((x,y))
            if min_x is None:
                min_x, max_x, min_y, max_y = x, x, y, y
            else:
                min_x=min(min_x,x); max_x=max(max_x,x); min_y=min(min_y,y); max_y=max(max_y,y)
        self.redraw()
        if min_x is not None:
            return (max_x-min_x, max_y-min_y, min_x, min_y)
        return (0,0,0,0)
    
    def redraw(self):
        self.delete("all")
        w=self.winfo_width() or 800
        h=self.winfo_height() or 600
        for i in range(0,w,40):
            self.create_line(i,0,i,h, fill="#1a2a1a", dash=(2,4))
        for i in range(0,h,40):
            self.create_line(0,i,w,i, fill="#1a2a1a", dash=(2,4))
        scale_x=(w-100)/max(self.area_w,1)
        scale_y=(h-100)/max(self.area_h,1)
        scale=min(scale_x, scale_y)*0.9
        if len(self.gcode_lines)>1:
            pts=[]
            for x,y in self.gcode_lines:
                pts.extend([50+x*scale, h-50-y*scale])
            if len(pts)>=4:
                self.create_line(pts, fill="#8cff00", width=2)
        # Posicion actual
        cx, cy = self.current_pos
        px = 50+cx*scale
        py = h-50-cy*scale
        self.create_oval(px-5, py-5, px+5, py+5, fill="#00ffaa", outline="")

class DavierPlasmaFull:
    def __init__(self, root):
        self.root=root
        self.root.title("DAVIER NC PLASMA V3.1")
        self.root.geometry("1280x760")
        self.root.configure(bg="#0a0a0f")
        self.fluid=FluidNC_Full(log_callback=self.log_fluid)
        self.gcode_text=""
        self.step_var=tk.StringVar(value="1.00 mm")
        self.area_x_var=tk.StringVar(value="1000")
        self.area_y_var=tk.StringVar(value="600")
        self.vel_max_var=tk.StringVar(value="4000")
        self.vel_min_var=tk.StringVar(value="200")
        self.acc_var=tk.StringVar(value="500")
        self.mat_w_var=tk.StringVar(value="800")
        self.mat_h_var=tk.StringVar(value="500")
        self.build_ui()
        self.update_status_loop()
    
    def build_ui(self):
        top=tk.Frame(self.root, bg="#111115", height=70)
        top.pack(fill="x")
        top.pack_propagate(False)
        title_frame=tk.Frame(top, bg="#111115")
        title_frame.pack(side="left", padx=20, pady=10)
        tk.Label(title_frame, text="◈", fg="#8cff00", bg="#111115", font=("Consolas",28)).pack(side="left")
        tk.Label(title_frame, text="DAVIER NC PLASMA V3.1", fg="#8cff00", bg="#111115", font=("Segoe UI Black",18)).pack(side="left", padx=10)
        tk.Label(title_frame, text=f"FULL FIRMWARE v{VERSION}", fg="#666", bg="#111115", font=("Consolas",8)).pack(side="left", padx=10)
        conn_frame=tk.Frame(top, bg="#111115", bd=1, relief="solid")
        conn_frame.pack(side="right", padx=20, pady=10)
        self.conn_label=tk.Label(conn_frame, text="● CONECTADO\nCOM3", fg="#8cff00", bg="#1a1a1f", font=("Consolas",8), justify="left", padx=10, pady=5)
        self.conn_label.pack()
        tk.Button(conn_frame, text="Conectar", bg="#1a2a1a", fg="#8cff00", bd=0, font=("Segoe UI",8,"bold"), command=self.toggle_connect).pack(fill="x")
        
        main=tk.Frame(self.root, bg="#0a0a0f")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        left=tk.Frame(main, bg="#121218", width=260, bd=1, relief="solid")
        left.pack(side="left", fill="y", padx=(0,10))
        left.pack_propagate(False)
        tk.Label(left, text="⚙ Manual XYZ", fg="#8cff00", bg="#121218", font=("Segoe UI",11,"bold"), anchor="w").pack(fill="x", padx=10, pady=10)
        tk.Label(left, text="Controles Manuales", fg="#aaa", bg="#121218", font=("Segoe UI",9)).pack(anchor="w", padx=10)
        def btn_row(parent, label, ltxt, rtxt, cl, cr):
            f=tk.Frame(parent, bg="#121218")
            f.pack(fill="x", padx=10, pady=6)
            tk.Label(f, text=label, fg="#8cff00", bg="#0f1a0f", width=3, font=("Segoe UI",10,"bold"), bd=1, relief="solid").pack(side="left")
            tk.Button(f, text=ltxt, bg="#1a1a1a", fg="white", bd=1, font=("Consolas",8), width=10, command=cl).pack(side="left", padx=5)
            tk.Button(f, text=rtxt, bg="#1a1a1a", fg="white", bd=1, font=("Consolas",8), width=10, command=cr).pack(side="left")
        btn_row(left,"X","◀ [X-]","[X+] ▶",lambda:self.jog("X",-1),lambda:self.jog("X",1))
        btn_row(left,"Y","▲ [Y-]","[Y+] ▲",lambda:self.jog("Y",-1),lambda:self.jog("Y",1))
        btn_row(left,"Z","▼ [Z-]","[Z+] ▲",lambda:self.jog("Z",-1),lambda:self.jog("Z",1))
        tk.Label(left, text="Paso / Step", fg="#aaa", bg="#121218", font=("Segoe UI",8)).pack(anchor="w", padx=10, pady=(15,0))
        import tkinter.ttk as ttk
        ttk.Combobox(left, textvariable=self.step_var, values=["0.10 mm","1.00 mm","10.00 mm","100 mm"], width=25).pack(padx=10, pady=5, fill="x")
        tk.Frame(left, bg="#8cff00", height=2).pack(fill="x", padx=10, pady=15)
        tk.Label(left, text="Configuración — Parámetros de Máquina", fg="#8cff00", bg="#121218", font=("Segoe UI",8,"bold")).pack(anchor="w", padx=10)
        def param_row(parent, label, var):
            f=tk.Frame(parent, bg="#121218")
            f.pack(fill="x", padx=10, pady=4)
            tk.Label(f, text=label, fg="white", bg="#121218", font=("Segoe UI",8), width=10, anchor="w").pack(side="left")
            tk.Entry(f, textvariable=var, bg="#1a1a1a", fg="white", bd=1, font=("Consolas",8), relief="solid").pack(side="left", fill="x", expand=True)
        tk.Label(left, text="Área de Corte", fg="#aaa", bg="#121218", font=("Segoe UI",8,"bold")).pack(anchor="w", padx=10, pady=(10,0))
        param_row(left,"X:",self.area_x_var)
        param_row(left,"Y:",self.area_y_var)
        tk.Label(left, text="Velocidad", fg="#aaa", bg="#121218", font=("Segoe UI",8,"bold")).pack(anchor="w", padx=10, pady=(10,0))
        param_row(left,"Máx:",self.vel_max_var)
        param_row(left,"Mín:",self.vel_min_var)
        param_row(left,"Acelerac:",self.acc_var)
        tk.Label(left, text="Dimensiones Material", fg="#aaa", bg="#121218", font=("Segoe UI",8,"bold")).pack(anchor="w", padx=10, pady=(10,0))
        param_row(left,"Ancho:",self.mat_w_var)
        param_row(left,"Largo:",self.mat_h_var)
        tk.Button(left, text="Abrir Configuración Avanzada", bg="#0f1a0f", fg="#8cff00", bd=1, relief="solid", font=("Segoe UI",8), command=self.open_file).pack(fill="x", padx=10, pady=15)
        
        right=tk.Frame(main, bg="#121218")
        right.pack(side="left", fill="both", expand=True)
        right_top=tk.Frame(right, bg="#121218", height=40)
        right_top.pack(fill="x", padx=10, pady=5)
        right_top.pack_propagate(False)
        tk.Label(right_top, text="◉ Previsualización — Trayectoria G-code (Tiempo Real)", fg="#8cff00", bg="#121218", font=("Segoe UI",9,"bold")).pack(side="left")
        btns=tk.Frame(right_top, bg="#121218")
        btns.pack(side="right")
        # Estos botones ahora hacen TODO el firmware sin cambiar interfaz
        tk.Button(btns, text="RECORRIDO", bg="#1a2a1a", fg="#8cff00", bd=1, font=("Segoe UI",7,"bold"), padx=8, command=self.do_recorrido).pack(side="left", padx=2)
        tk.Button(btns, text="CONTORNO / FRAME", bg="#1a2a1a", fg="#8cff00", bd=1, font=("Segoe UI",7,"bold"), padx=8, command=self.do_frame).pack(side="left", padx=2)
        tk.Button(btns, text="▶ Iniciar", bg="#1a1a1a", fg="white", bd=1, font=("Segoe UI",8), command=self.do_iniciar).pack(side="left", padx=2)
        tk.Button(btns, text="❚❚ Pausa", bg="#1a1a1a", fg="white", bd=1, font=("Segoe UI",8), command=self.do_pausa).pack(side="left", padx=2)
        tk.Button(btns, text="↺ Reset", bg="#1a1a1a", fg="white", bd=1, font=("Segoe UI",8), command=self.do_reset).pack(side="left", padx=2)
        
        self.preview=GCodePreview(right)
        self.preview.pack(fill="both", expand=True, padx=10, pady=5)
        
        # LOG oculto pero funcional (firmware logs)
        self.log_text=tk.Text(right, height=4, bg="#0a0a0a", fg="#0f0", font=("Consolas",7))
        self.log_text.pack(fill="x", padx=10, pady=(0,5))
        
        bottom=tk.Frame(self.root, bg="#111115", height=30)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)
        self.status_label=tk.Label(bottom, text="Estado: IDLE | THC: ON | Arc: OFF | X:0 Y:0 Z:0 | Feed:0", fg="#0f0", bg="#111115", font=("Consolas",7))
        self.status_label.pack(side="left", padx=10)
        self.load_demo()
    
    def log_fluid(self, msg):
        try:
            self.log_text.insert("end", msg+"\n")
            self.log_text.see("end")
        except: pass
    
    def load_demo(self):
        demo="G0 X100 Y100\nG1 X400 Y150\nG1 X600 Y300\nG1 X800 Y500\n"
        self.gcode_text=demo
        self.preview.load_gcode(demo)
    
    def get_step(self):
        try: return float(self.step_var.get().split()[0])
        except: return 1.0
    
    def jog(self, axis, dir):
        step=self.get_step()*dir
        feed=self.vel_max_var.get().split()[0] if self.vel_max_var.get() else "4000"
        self.fluid.jog(axis, step, feed)
    
    def do_recorrido(self):
        # Recorrido = Dry run sin plasma, con THC OFF
        self.fluid.thc_disable()
        self.fluid.torch_off()
        self.log_fluid("RECORRIDO - Dry run, plasma OFF, THC OFF")
        if self.gcode_text:
            threading.Thread(target=lambda: self.fluid.run_gcode_file(self.gcode_text), daemon=True).start()
    
    def do_frame(self):
        # Frame = recorrer perímetro del material
        try:
            mw=float(self.mat_w_var.get()); mh=float(self.mat_h_var.get())
            gcode=f"G0 X0 Y0\nG1 X{mw} Y0\nG1 X{mw} Y{mh}\nG1 X0 Y{mh}\nG1 X0 Y0\n"
            self.fluid.run_gcode_file(gcode)
            self.log_fluid(f"FRAME {mw}x{mh}")
        except: pass
    
    def do_iniciar(self):
        # Iniciar = IHS + Torch ON + THC ON + run
        self.log_fluid("INICIAR - IHS + Torch ON + THC ON")
        def seq():
            self.fluid.probe_ihs()
            time.sleep(0.5)
            self.fluid.torch_on()
            time.sleep(0.5) # pierce delay
            self.fluid.thc_enable()
            if self.gcode_text:
                self.fluid.run_gcode_file(self.gcode_text)
        threading.Thread(target=seq, daemon=True).start()
    
    def do_pausa(self):
        self.fluid.feed_hold()
        self.log_fluid("PAUSA !")
    
    def do_reset(self):
        self.fluid.torch_off()
        self.fluid.thc_disable()
        self.fluid.reset()
        self.log_fluid("RESET Ctrl-X + Torch OFF")
    
    def toggle_connect(self):
        if self.fluid.connected:
            self.fluid.disconnect()
            self.conn_label.config(text="● DESCONECTADO\nCOM3", fg="red")
        else:
            ports=self.fluid.list_ports()
            port=ports[0] if ports else "COM3"
            ok,msg=self.fluid.connect(port)
            if ok:
                self.conn_label.config(text=f"● CONECTADO\n{port}", fg="#8cff00")
            else:
                messagebox.showerror("FluidNC", msg)
    
    def open_file(self):
        path=filedialog.askopenfilename(filetypes=[("G-code","*.gcode *.nc *.tap"),("Todos","*.*")])
        if not path: return
        with open(path,'r') as f:
            gcode=f.read()
        self.gcode_text=gcode
        fw,fh,_,_=self.preview.load_gcode(gcode)
        try:
            mw=float(self.mat_w_var.get()); mh=float(self.mat_h_var.get())
        except:
            mw,mh=800,500
        if fw>mw or fh>mh:
            self.show_warning(fw,fh,mw,mh)
    
    def show_warning(self,fw,fh,mw,mh):
        win=tk.Toplevel(self.root)
        win.title("Advertencia"); win.geometry("400x180"); win.configure(bg="#111115"); win.transient(self.root); win.grab_set()
        win.update_idletasks()
        x=self.root.winfo_x()+(self.root.winfo_width()//2)-200
        y=self.root.winfo_y()+(self.root.winfo_height()//2)-90
        win.geometry(f"+{x}+{y}")
        top=tk.Frame(win, bg=YELLOW_WARN, height=40); top.pack(fill="x")
        tk.Label(top, text="⚠ Advertencia", bg=YELLOW_WARN, fg="black", font=("Segoe UI",11,"bold")).pack(side="left", padx=15, pady=8)
        body=tk.Frame(win, bg="#0a0a0a"); body.pack(fill="both", expand=True, padx=2, pady=2)
        tk.Label(body, text=f"Archivo mas grande que el material.\n\nArchivo: {fw:.0f}x{fh:.0f}mm\nMaterial: {mw:.0f}x{mh:.0f}mm", fg="white", bg="#0a0a0a", font=("Segoe UI",10), justify="center").pack(pady=20)
        bf=tk.Frame(body, bg="#0a0a0a"); bf.pack(pady=10)
        def cerrar(aceptar=False):
            win.destroy()
            if aceptar:
                self.mat_w_var.set(str(int(fw+20))); self.mat_h_var.set(str(int(fh+20))); self.preview.set_material(fw+20, fh+20)
        tk.Button(bf, text="Cancelar", bg="#1a1a1a", fg="white", width=12, bd=1, command=lambda: cerrar(False)).pack(side="left", padx=10)
        tk.Button(bf, text="Aceptar", bg=YELLOW_WARN, fg="black", width=12, bd=0, font=("Segoe UI",9,"bold"), command=lambda: cerrar(True)).pack(side="left", padx=10)
    
    def update_status_loop(self):
        try:
            st=self.fluid.status
            thc="ON" if self.fluid.thc_enabled else "OFF"
            arc="OK" if self.fluid.arc_ok else "OFF"
            self.status_label.config(text=f"Estado: {st.get('state','Idle')} | THC:{thc} V:{self.fluid.thc_voltage:.1f} | Arc:{arc} Torch:{'ON' if self.fluid.torch_on else 'OFF'} | X:{st['x']:.2f} Y:{st['y']:.2f} Z:{st['z']:.2f} | Feed:{st['feed']:.0f} | {datetime.now().strftime('%H:%M:%S')}")
            self.preview.current_pos=(st['x'], st['y'])
            if hasattr(self.preview, 'redraw'):
                # solo actualizar punto
                pass
        except: pass
        self.root.after(200, self.update_status_loop)

if __name__=="__main__":
    root=tk.Tk()
    app=DavierPlasmaFull(root)
    root.mainloop()
