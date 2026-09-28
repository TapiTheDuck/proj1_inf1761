# prep_textures.py — rode uma vez, a partir da pasta scene_graph_distr/python
from pathlib import Path
from PIL import Image
import numpy as np

textures_dir = Path("textures")
files = ["sun.png", "mercury.png", "earth.png", "moon.png"]

for name in files:
    path = textures_dir / name
    img = Image.open(path).convert("RGBA")
    arr = np.array(img)
    alpha = arr[:, :, 3]
    mask = alpha > 10          # pixels "de verdade" (não-transparentes)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        print(f"{name}: nada encontrado, pulando")
        continue

    x0, x1 = xs.min(), xs.max()
    y0, y1 = ys.min(), ys.max()
    cropped = img.crop((x0, y0, x1 + 1, y1 + 1))

    # garante quadrado perfeito, sem esticar (preenche o mínimo necessário)
    w, h = cropped.size
    side = max(w, h)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(cropped, ((side - w) // 2, (side - h) // 2), cropped)

    square.save(path)
    print(f"{name}: {img.size} -> cortado para {square.size}")