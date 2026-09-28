# cnc_v3_1_grilla_dinamica.py
# CNC v3.1 - Mesa 1800 x 2800 mm con grilla dinámica
# Autor: David - Barranquilla

import math

class CNCv31:
    def __init__(self, width=1800, height=2800):
        self.width = width  # X
        self.height = height # Y
        self.version = "v3.1"
    
    def generar_grilla_dinamica(self, spacing_x=100, spacing_y=100, 
                                adaptativa=False, margen=20):
        """
        Genera grilla dinámica.
        - spacing_x/y: separación base
        - adaptativa: si es True, la grilla se hace más densa en el centro
        - margen: margen de seguridad
        """
        puntos = []
        
        # Grilla base
        x_steps = int((self.width - 2*margen) / spacing_x)
        y_steps = int((self.height - 2*margen) / spacing_y)

        for i in range(x_steps + 1):
            for j in range(y_steps + 1):
                x = margen + i * spacing_x
                y = margen + j * spacing_y

                # Modo dinámico: más densidad en el centro
                if adaptativa:
                    centro_x = self.width / 2
                    centro_y = self.height / 2
                    dist_centro = math.sqrt((x-centro_x)**2 + (y-centro_y)**2)
                    # Si está cerca del centro, duplica puntos intermedios
                    if dist_centro < 400:
                        # Punto intermedio para mayor densidad
                        if i < x_steps and j < y_steps:
                            puntos.append((x + spacing_x/2, y + spacing_y/2))

                puntos.append((x, y))
        
        print(f"[CNC {self.version}] Grilla generada: {len(puntos)} puntos")
        print(f"Mesa: {self.width}x{self.height}mm | Spacing: {spacing_x}x{spacing_y}")
        return puntos

    def exportar_gcode(self, puntos, archivo="grilla_v3_1.gcode", z_safe=5, z_work=-2, feed=1200):
        """ Exporta a G-code para fresadora """
        with open(archivo, "w") as f:
            f.write(f"; CNC {self.version} - {self.width}x{self.height}\n")
            f.write(f"; Grilla Dinamica - {len(puntos)} puntos\n")
            f.write("G21 ; mm\n")
            f.write("G90 ; absoluto\n")
            f.write(f"G0 Z{z_safe}\n")
            
            for x, y in puntos:
                f.write(f"G0 X{x:.2f} Y{y:.2f}\n")
                f.write(f"G1 Z{z_work} F{feed}\n")
                f.write(f"G0 Z{z_safe}\n")
            
            f.write("M30 ; fin\n")
        print(f"G-code guardado en: {archivo}")
        return archivo

    def exportar_svg(self, puntos, archivo="grilla_v3_1.svg"):
        """ Para vista previa en tu app """
        svg = f[STRIPPED 88 bytes]
        svg += f'<rect width="{self.width}" height="{self.height}" fill="#111" stroke="#444"/>\n'
        for x, y in puntos:
            svg += f'<circle cx="{x}" cy="{y}" r="3" fill="#00FF88"/>\n'
        svg += '</svg>'
        with open(archivo, "w") as f:
            f.write(svg)
        print(f"SVG guardado en: {archivo}")

# --- USO ---
if __name__ == "__main__":
    cnc = CNCv31(width=1800, height=2800)
    
    # Cambia aquí a True si quieres la grilla dinámica adaptativa
    puntos = cnc.generar_grilla_dinamica(
        spacing_x=100, 
        spacing_y=100, 
        adaptativa=True, 
        margen=25
    )
    
    cnc.exportar_gcode(puntos)
    cnc.exportar_svg(puntos)
