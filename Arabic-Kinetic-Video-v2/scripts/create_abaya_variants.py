#!/usr/bin/env python3
"""Create four aligned transparent abaya PNG states from one approved master cutout."""
from __future__ import annotations
from pathlib import Path
import argparse
import math
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / 'public' / 'images'
MASTER = IMG_DIR / 'abaya-master.webp'


def clip_overlay(overlay: Image.Image, alpha: Image.Image) -> Image.Image:
    oa = overlay.getchannel('A')
    import PIL.ImageChops as ImageChops
    overlay.putalpha(ImageChops.multiply(oa, alpha))
    return overlay


def flower(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0) -> None:
    gold = (197, 158, 89, 245)
    pink = (201, 79, 118, 240)
    r = max(3, int(5 * scale))
    for i in range(5):
        a = i * math.tau / 5
        px = cx + math.cos(a) * 7 * scale
        py = cy + math.sin(a) * 7 * scale
        rr = max(2, int(4 * scale))
        draw.ellipse((px-rr, py-rr, px+rr, py+rr), fill=pink, outline=gold, width=1)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=gold)


def draw_vine(draw: ImageDraw.ImageDraw, x: int, y0: int, y1: int, side: int) -> None:
    pts = []
    steps = 32
    for i in range(steps + 1):
        t = i / steps
        y = y0 + (y1-y0)*t
        xoff = math.sin(t*math.pi*7) * 7
        pts.append((x + xoff, y))
    draw.line(pts, fill=(184, 146, 75, 235), width=4, joint='curve')
    for i in range(1, 12):
        t = i / 12
        y = int(y0 + (y1-y0)*t)
        xoff = math.sin(t*math.pi*7)*7
        xx = x + xoff
        a = math.pi/2 if i % 2 else -math.pi/2
        direction = side * (1 if i % 2 else -1)
        lx = xx + direction * 15
        ly = y - 7
        draw.ellipse((lx-7, ly-3, lx+7, ly+3), fill=(171, 135, 69, 230), outline=(210, 177, 113, 235), width=1)
        if i % 3 == 0:
            flower(draw, int(xx), y, 0.55)


def build() -> None:
    if not MASTER.exists():
        raise FileNotFoundError(f'Master abaya cutout missing: {MASTER}')
    base = Image.open(MASTER).convert('RGBA')
    alpha = base.getchannel('A')
    # The master is the definitive transparent silhouette; all derivatives retain its geometry.
    base.save(IMG_DIR / 'element-01.png', optimize=True)

    # 02: subtle black-on-black jacquard. The garment pixels stay identical.
    brocade = base.copy()
    overlay = Image.new('RGBA', base.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    for y in range(240, 1450, 112):
        for x in range(330, 720, 76):
            # alternating small damask curls and lozenges in deep charcoal
            col = (52, 50, 52, 74)
            d.arc((x-20, y-26, x+20, y+26), 195, 345, fill=col, width=3)
            d.arc((x-20, y-26, x+20, y+26), 15, 165, fill=col, width=3)
            d.polygon([(x, y-19), (x+9, y), (x, y+19), (x-9, y)], outline=(48,46,48,68))
    # Additional low-contrast arabesque panels at sleeves.
    for y in range(430, 690, 48):
        d.arc((155, y-22, 295, y+22), 205, 335, fill=(55,53,55,60), width=3)
        d.arc((730, y-22, 870, y+22), 205, 335, fill=(55,53,55,60), width=3)
    overlay = clip_overlay(overlay, alpha)
    brocade = Image.alpha_composite(brocade, overlay)
    brocade.save(IMG_DIR / 'element-02.png', optimize=True)

    # 03: visible gold and rose embroidery along front edges, cuffs and sleeve panels.
    ornate = base.copy()
    overlay = Image.new('RGBA', base.size, (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    # front embroidery rails (symmetrical, same front-facing perspective)
    draw_vine(d, 440, 130, 1480, -1)
    draw_vine(d, 584, 130, 1480, 1)
    # center seam fine metallic stitch
    d.line([(512, 175), (512, 1490)], fill=(158, 124, 66, 170), width=2)
    # sleeve/cuff embroidery bands
    d.line([(145, 645), (265, 704), (390, 727)], fill=(189, 151, 80, 225), width=5, joint='curve')
    d.line([(635, 727), (760, 704), (880, 645)], fill=(189, 151, 80, 225), width=5, joint='curve')
    for cx, cy in [(230,640),(280,675),(338,700),(785,640),(735,675),(677,700),
                   (450,300),(450,520),(450,760),(450,1000),(450,1250),
                   (574,300),(574,520),(574,760),(574,1000),(574,1250)]:
        flower(d, cx, cy, 0.8 if cy < 740 else 0.65)
    # tiny gold dots/stitches adjacent to rails
    for y in range(190, 1440, 28):
        for x in (426, 454, 570, 598):
            d.ellipse((x-2,y-2,x+2,y+2), fill=(216,184,117,220))
    overlay = clip_overlay(overlay, alpha)
    ornate = Image.alpha_composite(ornate, overlay)
    ornate.save(IMG_DIR / 'element-03.png', optimize=True)

    # 04: same embroidery and cut, with the textile itself visibly sheer.
    sheer = ornate.copy()
    rgba = sheer.load()
    for y in range(sheer.height):
        # Slightly lighter weave and gently translucent fabric; alpha outside garment remains zero.
        for x in range(sheer.width):
            r,g,b,a = rgba[x,y]
            if a:
                factor = 0.62
                rgba[x,y] = (min(255, int(r*0.68+20)), min(255, int(g*0.68+20)), min(255, int(b*0.68+22)), int(a*factor))
    # Preserve embroidery a little stronger than the fabric by compositing its design once more
    # with restrained opacity, still using the same base alpha silhouette.
    extra = Image.new('RGBA', sheer.size, (0,0,0,0))
    ed = ImageDraw.Draw(extra)
    draw_vine(ed, 440, 130, 1480, -1)
    draw_vine(ed, 584, 130, 1480, 1)
    for cx,cy in [(230,640),(280,675),(338,700),(785,640),(735,675),(677,700),
                  (450,520),(450,1000),(574,520),(574,1000)]: flower(ed,cx,cy,0.75)
    extra.putalpha(Image.eval(extra.getchannel('A'), lambda a: int(a*0.55)))
    sheer = Image.alpha_composite(sheer, extra)
    sheer.save(IMG_DIR / 'element-04.png', optimize=True)

    # Downsample all four states together to a 768x1152 asset canvas (slightly above
    # their 760x1140 display size) while preserving the identical silhouette and center.
    target_size = (768, 1152)
    for i in range(1, 5):
        p = IMG_DIR / f'element-{i:02d}.png'
        im = Image.open(p).convert('RGBA')
        im = im.resize(target_size, Image.Resampling.LANCZOS)
        im.save(p, optimize=True)

    # Geometry/alpha validation: identical canvas, non-empty transparent PNGs.
    results=[]
    for i in range(1,5):
        p=IMG_DIR/f'element-{i:02d}.png'
        im=Image.open(p).convert('RGBA')
        bb=im.getchannel('A').point(lambda a: 255 if a>20 else 0).getbbox()
        results.append({'file':p.name,'size':im.size,'alpha_bbox':bb,'alpha_extrema':im.getchannel('A').getextrema()})
    if len({tuple(r['size']) for r in results}) != 1:
        raise RuntimeError('Image dimensions differ')
    if len({tuple(r['alpha_bbox']) for r in results}) != 1:
        raise RuntimeError(f'Abaya geometry differs between variants: {results}')
    print('ABAYA ASSETS: PASS')
    for r in results: print(r)

if __name__ == '__main__':
    build()
