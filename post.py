import sys, numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont

src, dst = sys.argv[1], sys.argv[2]
wm_text = sys.argv[3] if len(sys.argv) > 3 else ""

im = Image.open(src).convert("RGB")
w, h = im.size
s = w / 1080.0
a = np.asarray(im).astype(np.float32) / 255.0

soft = np.asarray(im.filter(ImageFilter.GaussianBlur(0.65 * s))).astype(np.float32) / 255.0
a = a * 0.68 + soft * 0.32

lum = a @ np.array([0.2126, 0.7152, 0.0722])
bright = np.clip((lum - 0.70) / 0.30, 0, 1)[..., None] * a
g = Image.fromarray((bright * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18 * s))
a = 1.0 - (1.0 - a) * (1.0 - np.asarray(g).astype(np.float32) / 255.0 * 0.45)

yy, xx = np.mgrid[0:h, 0:w]
d = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / np.sqrt(2)
a *= (1.0 - 0.25 * np.clip((d - 0.38) / 0.62, 0, 1) ** 1.6)[..., None]

rng = np.random.default_rng(7)
n = rng.normal(0, 1, (h, w)).astype(np.float32)
n = np.asarray(
    Image.fromarray(((n * 0.25 + 0.5).clip(0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6 * s))
).astype(np.float32) / 255.0 - 0.5
a += (n * 0.035 * (1.2 - lum.clip(0, 1)))[..., None]

out_im = Image.fromarray((a.clip(0, 1) * 255).astype(np.uint8)).convert("RGBA")
if wm_text:
    ov = Image.new("RGBA", out_im.size, (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    fsize = max(18, int(w * 0.032))
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fsize)
    except Exception:
        font = ImageFont.load_default()
    bb = dr.textbbox((0, 0), wm_text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    tx = (w - tw) // 2
    ty = int(h * 0.87)
    dr.text((tx + 2, ty + 2), wm_text, font=font, fill=(0, 0, 0, 110))
    dr.text((tx, ty), wm_text, font=font, fill=(255, 255, 255, 130))
    out_im = Image.alpha_composite(out_im, ov)

out_im.convert("RGB").save(dst)
