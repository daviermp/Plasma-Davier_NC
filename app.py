"""
CNC v3.1 - 1800x2800 Grilla Dinámica
App final lista para GitHub
Autor: Davier - Barranquilla, CO
Version: 3.1.0

Uso:
  python cnc_v3_1_final_app.py --spacing 100 --adaptive --preview
  python cnc_v3_1_final_app.py --width 1800 --height 2800 --spacing-x 100 --spacing-y 100 --export all
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
                        # Inserta punto intermedio para mayor densidad central (dinámico)
                        if i < x_steps and j < y_steps:
                            puntos.append((x + spacing_x/2, y + spacing_y/2))

        print(f"[{self.version}] Grilla: {len(puntos)} puntos | Mesa {self.width}x{self.height} | Spacing {spacing_x}x{spacing_y} | Adaptive={adaptive}")
        return puntos, meta

    def exportar_gcode(self, puntos, output_dir=Path("."), z_safe=5, z_work=-1.5, feed=1500, spindle=12000):
        path = output_dir / f"cnc_{self.width}x{self.height}_grilla.gcode"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"; CNC {self.version} - {self.width}x{self.height} Grilla Dinamica\n")
            f.write(f"; Generado: {datetime.now().isoformat()}\n")
            f.write(f"; Puntos: {len(puntos)}\n")
            f.write("G21 ; Unidades mm\n")
            f.write("G90 ; Coordenadas absolutas\n")
            f.write("G17 ; Plano XY\n")
            f.write(f"M3 S{spindle} ; Spindle ON\n")
            f.write(f"G0 Z{z_safe}\n")
            f.write("G0 X0 Y0\n")

            for x, y in puntos:
                f.write(f"\n; Punto {x:.1f},{y:.1f}\n")
                f.write(f"G0 X{x:.2f} Y{y:.2f}\n")
                f.write(f"G1 Z{z_work} F{feed//2}\n")
                f.write(f"G0 Z{z_safe}\n")

            f.write("\nM5 ; Spindle OFF\n")
            f.write("M30 ; Fin programa\n")
        return path

    def exportar_svg(self, puntos, output_dir=Path(".")):
        path = output_dir / f"cnc_{self.width}x{self.height}_grilla.svg"
        svg_content = [
            f'<svg width="{self.width}" height="{self.height}" viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">',
            f'<rect width="{self.width}" height="{self.height}" fill="#0a0a0a" stroke="#333" stroke-width="2"/>',
            f'<text x="20" y="30" fill="#888" font-family="monospace" font-size="24">CNC {self.version} {self.width}x{self.height} - {len(puntos)} pts</text>'
        ]
        for x, y in puntos:
            svg_content.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#00FF88" opacity="0.8"><title>{x:.1f},{y:.1f}</title></circle>')
        svg_content.append('</svg>')
        
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(svg_content))
        return path

    def exportar_json(self, puntos, meta, output_dir=Path(".")):
        path = output_dir / f"cnc_{self.width}x{self.height}_grilla.json"
        data = {
            "meta": meta,
            "config": {"width": self.width, "height": self.height, "margen": self.margen},
            "puntos": [{"x": round(x,2), "y": round(y,2)} for x,y in puntos]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

def main():
    parser = argparse.ArgumentParser(description=f"CNC v3.1 1800x2800 - Grilla Dinamica - v{VERSION}")
    parser.add_argument("--width", type=int, default=1800, help="Ancho mesa en mm")
    parser.add_argument("--height", type=int, default=2800, help="Largo mesa en mm")
    parser.add_argument("--spacing", type=int, default=None, help="Spacing uniforme (atajo para x e y)")
    parser.add_argument("--spacing-x", type=int, default=100, help="Spacing X")
    parser.add_argument("--spacing-y", type=int, default=100, help="Spacing Y")
    parser.add_argument("--margen", type=int, default=25, help="Margen seguridad")
    parser.add_argument("--adaptive", action="store_true", help="Activa grilla dinámica adaptativa (más densa en centro)")
    parser.add_argument("--density-center", type=int, default=400, help="Radio de densidad central en mm")
    parser.add_argument("--export", choices=["gcode","svg","json","all"], default="all", help="Qué exportar")
    parser.add_argument("--out", type=str, default="./output", help="Carpeta salida")
    parser.add_argument("--z-safe", type=float, default=5)
    parser.add_argument("--z-work", type=float, default=-1.5)
    parser.add_argument("--feed", type=int, default=1500)

    args = parser.parse_args()

    if args.spacing:
        args.spacing_x = args.spacing
        args.spacing_y = args.spacing

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cnc = CNCv31(width=args.width, height=args.height, margen=args.margen)
    puntos, meta = cnc.generar_grilla_dinamica(
        spacing_x=args.spacing_x,
        spacing_y=args.spacing_y,
        adaptive=args.adaptive,
        density_center=args.density_center
    )

    exported = []
    if args.export in ["gcode", "all"]:
        exported.append(cnc.exportar_gcode(puntos, out_dir, z_safe=args.z_safe, z_work=args.z_work, feed=args.feed))
    if args.export in ["svg", "all"]:
        exported.append(cnc.exportar_svg(puntos, out_dir))
    if args.export in ["json", "all"]:
        exported.append(cnc.exportar_json(puntos, meta, out_dir))

    print("\n✓ Archivos generados:")
    for p in exported:
        print(f"  - {p}")

    print(f"\nListo para push a GitHub, Davier.")

if __name__ == "__main__":
    main()
