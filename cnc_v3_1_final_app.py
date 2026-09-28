"""
CNC v3.1 - 1800x2800 Grilla Dinámica
App final lista para 【entity-【entity-GitHub¦canonical_name=GitHub】¦canonical_name=【entity-GitHub¦canonical_name=GitHub】】
Autor: Davier - Barranquilla, CO
Version: 3.1.0
"""
import argparse
import math
import json
from pathlib import Path
from datetime import datetime

VERSION = "3.1.0"

class CNCv31:
    def __init__(self, width=1800, height=2800, margen=25):
        self.width = width
        self.height = height
        self.margen = margen
        self.version = f"v{VERSION}"

    def generar_grilla_dinamica(self, spacing_x=100, spacing_y=100, adaptive=False, density_center=400):
        puntos = []
        meta = {
            "version": self.version,
            "mesa": f"{self.width}x{self.height}",
            "spacing": f"{spacing_x}x{spacing_y}",
            "adaptive": adaptive,
            "timestamp": datetime.now().isoformat()
        }
        x_steps = int((self.width - 2*self.margen) // spacing_x)
        y_steps = int((self.height - 2*self.margen) // spacing_y)
        for i in range(x_steps + 1):
            for j in range(y_steps + 1):
                x = self.margen + i * spacing_x
                y = self.margen + j * spacing_y
                puntos.append((x, y))
                if adaptive:
                    cx, cy = self.width/2, self.height/2
                    dist = math.hypot(x-cx, y-cy)
                    if dist < density_center:
                        if i < x_steps and j < y_steps:
                            puntos.append((x + spacing_x/2, y + spacing_y/2))
        print(f"[{self.version}] Grilla: {len(puntos)} puntos")
        return puntos, meta

    def exportar_gcode(self, puntos, output_dir=Path("."), z_safe=5, z_work=-1.5, feed=1500, spindle=12000):
        path = output_dir / f"cnc_{self.width}x{self.height}_grilla.gcode"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"; CNC {self.version} - {self.width}x{self.height}\n")
            f.write("G21\nG90\n")
            f.write(f"M3 S{spindle}\nG0 Z{z_safe}\n")
            for x, y in puntos:
                f.write(f"G0 X{x:.2f} Y{y:.2f}\nG1 Z{z_work} F{feed//2}\nG0 Z{z_safe}\n")
            f.write("M5\nM30\n")
        return path

    def exportar_svg(self, puntos, output_dir=Path(".")):
        path = output_dir / f"cnc_{self.width}x{self.height}_grilla.svg"
        svg = [f[STRIPPED 166 bytes]]
        for x, y in puntos:
            svg.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#00FF88"/>')
        svg.append('</svg>')
        with open(path, "w") as f: f.write("\n".join(svg))
        return path

    def exportar_json(self, puntos, meta, output_dir=Path(".")):
        path = output_dir / f"cnc_{self.width}x{self.height}_grilla.json"
        data = {"meta": meta, "puntos": [{"x": round(x,2), "y": round(y,2)} for x,y in puntos]}
        with open(path, "w") as f: json.dump(data, f, indent=2)
        return path

def main():
    parser = argparse.ArgumentParser(description=f"CNC v3.1 1800x2800 v{VERSION}")
    parser.add_argument("--spacing", type=int, default=100)
    parser.add_argument("--adaptive", action="store_true")
    parser.add_argument("--out", type=str, default="./output")
    args = parser.parse_args()
    out_dir = Path(args.out); out_dir.mkdir(parents=True, exist_ok=True)
    cnc = CNCv31()
    puntos, meta = cnc.generar_grilla_dinamica(spacing_x=args.spacing, spacing_y=args.spacing, adaptive=args.adaptive)
    cnc.exportar_gcode(puntos, out_dir)
    cnc.exportar_svg(puntos, out_dir)
    cnc.exportar_json(puntos, meta, out_dir)
    print("✓ Listo en", out_dir)

if __name__ == "__main__":
    main()
