"""Genera los iconos de la PWA en app/frontend/icons/ (solo biblioteca estándar).

    python scripts/generar_iconos.py

Dibuja una mancuerna blanca sobre el verde de la aplicación. Se ejecuta a mano
cuando cambie el diseño; los PNG resultantes se guardan en el repositorio.
"""
import struct
import zlib
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "app" / "frontend" / "icons"
GREEN = (23, 107, 72)   # --primary de style.css
WHITE = (255, 255, 255)
SUPERSAMPLE = 3          # muestras por eje, para suavizar los bordes


def rounded_box(x, y, cx, cy, half_w, half_h, radius):
    """Distancia con signo a un rectángulo redondeado (negativa = dentro)."""
    qx = abs(x - cx) - (half_w - radius)
    qy = abs(y - cy) - (half_h - radius)
    outside = (max(qx, 0) ** 2 + max(qy, 0) ** 2) ** 0.5

    return outside + min(max(qx, qy), 0) - radius


def inside_dumbbell(x, y, scale):
    """Mancuerna centrada; `scale` reduce el dibujo (zona segura del maskable)."""
    x = 0.5 + (x - 0.5) / scale
    y = 0.5 + (y - 0.5) / scale
    shapes = (
        (0.50, 0.50, 0.26, 0.035, 0.035),   # barra
        (0.30, 0.50, 0.045, 0.19, 0.03),    # disco interior izquierdo
        (0.70, 0.50, 0.045, 0.19, 0.03),    # disco interior derecho
        (0.215, 0.50, 0.035, 0.13, 0.025),  # disco exterior izquierdo
        (0.785, 0.50, 0.035, 0.13, 0.025),  # disco exterior derecho
    )

    return any(
        rounded_box(x, y, cx, cy, hw, hh, r) <= 0
        for cx, cy, hw, hh, r in shapes
    )


def render(size, *, rounded_corners, glyph_scale):
    rows = []
    corner = 0.18  # radio de la esquina en fracción del lado

    for py in range(size):
        row = bytearray([0])  # filtro PNG "ninguno"

        for px in range(size):
            green_hits = white_hits = 0

            for sy in range(SUPERSAMPLE):
                for sx in range(SUPERSAMPLE):
                    x = (px + (sx + 0.5) / SUPERSAMPLE) / size
                    y = (py + (sy + 0.5) / SUPERSAMPLE) / size

                    if rounded_corners and rounded_box(
                        x, y, 0.5, 0.5, 0.5, 0.5, corner
                    ) > 0:
                        continue  # fuera del icono: transparente

                    if inside_dumbbell(x, y, glyph_scale):
                        white_hits += 1
                    else:
                        green_hits += 1

            total = SUPERSAMPLE * SUPERSAMPLE
            covered = green_hits + white_hits

            if covered == 0:
                row += bytes((0, 0, 0, 0))
                continue

            color = tuple(
                round((GREEN[i] * green_hits + WHITE[i] * white_hits) / covered)
                for i in range(3)
            )
            row += bytes(color) + bytes((round(255 * covered / total),))

        rows.append(bytes(row))

    return b"".join(rows)


def write_png(path, size, raw):
    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack(">I", len(data)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA 8 bits
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

    # (archivo, lado, esquinas redondeadas, escala del dibujo)
    icons = (
        ("icon-192.png", 192, True, 1.0),
        ("icon-512.png", 512, True, 1.0),
        # «maskable»: sin esquinas propias y con el dibujo en la zona segura
        # (80 % central) para que el sistema pueda recortarlo como quiera.
        ("icon-maskable-512.png", 512, False, 0.7),
        ("apple-touch-icon.png", 180, False, 0.85),
    )

    for name, size, rounded, scale in icons:
        write_png(
            OUTPUT / name, size,
            render(size, rounded_corners=rounded, glyph_scale=scale),
        )
        print(f"Generado {name}")


if __name__ == "__main__":
    main()
