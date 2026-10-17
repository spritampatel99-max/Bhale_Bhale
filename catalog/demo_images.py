"""Procedurally drawn product illustrations (original artwork, no licensing issues).

Used only by the demo seeding command so every seeded product has a real image
file saved through Django's ImageField. Each shape is drawn on a 1000x1000 grid.
"""
import io
import math

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE = 1600          # drawn at 2x and down-sampled for smooth edges
OUT = 800
K = SIZE / 1000


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Pen:
    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img, "RGBA")

    def leaf(self, p0, p1, width, fill):
        """Lens-shaped leaf from p0 to p1."""
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n, dx / n
        steps = 24
        left = [(x0 + dx * t / steps + nx * width / 2 * math.sin(math.pi * t / steps),
                 y0 + dy * t / steps + ny * width / 2 * math.sin(math.pi * t / steps)) for t in range(steps + 1)]
        right = [(x0 + dx * t / steps - nx * width / 2 * math.sin(math.pi * t / steps),
                  y0 + dy * t / steps - ny * width / 2 * math.sin(math.pi * t / steps)) for t in range(steps, -1, -1)]
        self.poly(left + right, fill)

    def s(self, v):
        return v * K

    def rect(self, x0, y0, x1, y1, fill, r=0):
        box = [self.s(x0), self.s(y0), self.s(x1), self.s(y1)]
        if r:
            self.d.rounded_rectangle(box, radius=self.s(r), fill=fill)
        else:
            self.d.rectangle(box, fill=fill)

    def ell(self, x0, y0, x1, y1, fill=None, outline=None, width=0):
        self.d.ellipse([self.s(x0), self.s(y0), self.s(x1), self.s(y1)], fill=fill, outline=outline, width=int(self.s(width)))

    def poly(self, pts, fill):
        self.d.polygon([(self.s(x), self.s(y)) for x, y in pts], fill=fill)

    def line(self, pts, fill, width=10):
        self.d.line([(self.s(x), self.s(y)) for x, y in pts], fill=fill, width=int(self.s(width)), joint="curve")

    def arc(self, x0, y0, x1, y1, a0, a1, fill, width=10):
        self.d.arc([self.s(x0), self.s(y0), self.s(x1), self.s(y1)], a0, a1, fill=fill, width=int(self.s(width)))

    def bar(self, p0, p1, width, fill):
        """Thick rotated bar between two points."""
        (x0, y0), (x1, y1) = p0, p1
        dx, dy = x1 - x0, y1 - y0
        n = math.hypot(dx, dy) or 1
        ox, oy = -dy / n * width / 2, dx / n * width / 2
        self.poly([(x0 + ox, y0 + oy), (x1 + ox, y1 + oy), (x1 - ox, y1 - oy), (x0 - ox, y0 - oy)], fill)


# ---- shapes: (pen, main, accent, dark, light) ------------------------------------------------
def headphones(p, m, a, d, l):
    p.arc(280, 170, 720, 650, 180, 360, d, 46)
    p.rect(235, 430, 345, 660, a, 45)
    p.rect(655, 430, 765, 660, a, 45)
    p.rect(300, 450, 360, 640, m, 28)
    p.rect(640, 450, 700, 640, m, 28)


def watch(p, m, a, d, l):
    p.rect(415, 170, 585, 830, m, 40)
    p.ell(320, 320, 680, 680, d)
    p.ell(350, 350, 650, 650, l)
    p.line([(500, 500), (500, 405)], d, 16)
    p.line([(500, 500), (565, 530)], a, 14)
    p.ell(485, 485, 515, 515, d)
    p.rect(678, 470, 705, 530, a, 10)


def phone(p, m, a, d, l):
    p.rect(350, 190, 650, 810, d, 55)
    p.rect(368, 225, 632, 775, m, 30)
    p.rect(440, 205, 560, 225, l, 10)
    for i in range(3):
        for j in range(3):
            p.rect(398 + j * 78, 300 + i * 100, 450 + j * 78, 352 + i * 100, a if (i + j) % 2 else l, 14)


def laptop(p, m, a, d, l):
    p.rect(265, 290, 735, 600, d, 28)
    p.rect(285, 310, 715, 580, m, 12)
    p.poly([(500, 330), (700, 330), (700, 560), (420, 560)], a)
    p.poly([(190, 625), (810, 625), (860, 700), (140, 700)], l)
    p.rect(440, 640, 560, 662, d, 10)


def speaker(p, m, a, d, l):
    p.rect(330, 220, 670, 790, d, 70)
    p.ell(385, 430, 615, 660, m)
    p.ell(425, 470, 575, 620, d)
    p.ell(470, 515, 530, 575, a)
    p.ell(440, 290, 560, 380, m)
    p.ell(475, 322, 525, 352, a)


def camera(p, m, a, d, l):
    p.rect(215, 350, 785, 710, d, 50)
    p.rect(340, 280, 520, 370, d, 24)
    p.rect(250, 380, 750, 440, m, 20)
    p.ell(360, 400, 640, 680, l)
    p.ell(385, 425, 615, 655, d)
    p.ell(425, 465, 575, 615, a)
    p.ell(470, 510, 520, 560, l)
    p.ell(670, 330, 730, 380, a)


def tshirt(p, m, a, d, l):
    p.poly([(370, 215), (630, 215), (820, 330), (735, 470), (665, 425), (665, 800), (335, 800), (335, 425), (265, 470), (180, 330)], m)
    p.ell(425, 160, 575, 320, a)
    p.line([(335, 425), (335, 800)], d, 5)
    p.rect(420, 560, 580, 640, a, 14)


def shoe(p, m, a, d, l):
    p.poly([(190, 640), (190, 380), (340, 350), (430, 470), (560, 500), (740, 560), (830, 640)], m)
    p.rect(165, 630, 840, 730, l, 50)
    p.poly([(190, 640), (190, 600), (830, 650), (830, 640)], a)
    for i in range(4):
        p.bar((360 + i * 55, 410 + i * 28), (430 + i * 55, 385 + i * 28), 16, l)
    p.poly([(640, 530), (800, 600), (830, 640), (600, 620)], a)


def bag(p, m, a, d, l):
    p.arc(345, 170, 655, 560, 180, 360, d, 36)
    p.poly([(250, 410), (750, 410), (820, 800), (180, 800)], m)
    p.poly([(250, 410), (750, 410), (770, 540), (230, 540)], a)
    p.rect(460, 500, 540, 580, l, 14)
    p.line([(230, 540), (770, 540)], d, 6)


def glasses(p, m, a, d, l):
    p.ell(200, 400, 460, 640, a)
    p.ell(540, 400, 800, 640, a)
    p.ell(200, 400, 460, 640, None, d, 26)
    p.ell(540, 400, 800, 640, None, d, 26)
    p.arc(450, 410, 550, 500, 200, 340, d, 24)
    p.line([(205, 450), (110, 420)], d, 24)
    p.line([(795, 450), (890, 420)], d, 24)
    p.line([(250, 470), (340, 430)], l, 12)
    p.line([(590, 470), (680, 430)], l, 12)


def lamp(p, m, a, d, l):
    p.ell(230, 250, 770, 800, (255, 226, 140, 80))
    p.poly([(380, 230), (620, 230), (730, 480), (270, 480)], m)
    p.rect(485, 470, 515, 730, d)
    p.ell(375, 700, 625, 780, d)
    p.ell(460, 440, 540, 520, a)
    p.rect(370, 215, 630, 245, a, 14)


def mug(p, m, a, d, l):
    p.ell(585, 400, 790, 650, None, m, 44)
    p.rect(290, 320, 650, 760, m, 60)
    p.ell(290, 290, 650, 380, d)
    p.ell(310, 300, 630, 365, a)
    p.rect(290, 560, 650, 610, a, 4)
    for x in (390, 470, 550):
        p.line([(x, 250), (x - 25, 190), (x + 5, 140)], l, 14)


def plant(p, m, a, d, l):
    for dx, h in ((-250, 330), (-120, 430), (0, 470), (120, 430), (250, 330)):
        tip = (500 + dx, 610 - h)
        p.leaf((500, 620), tip, 120, _mix(m, l, 0.15) if dx % 240 else m)
    p.poly([(360, 590), (640, 590), (590, 820), (410, 820)], a)
    p.rect(340, 570, 660, 625, _mix(a, d, 0.3), 16)


def clock(p, m, a, d, l):
    p.ell(240, 240, 760, 760, d)
    p.ell(275, 275, 725, 725, l)
    for i in range(12):
        t = math.radians(i * 30)
        r0, r1 = (190, 215) if i % 3 else (170, 215)
        p.line([(500 + math.sin(t) * r0, 500 - math.cos(t) * r0), (500 + math.sin(t) * r1, 500 - math.cos(t) * r1)], d, 10)
    p.line([(500, 500), (500, 345)], d, 18)
    p.line([(500, 500), (610, 560)], a, 14)
    p.ell(480, 480, 520, 520, a)


def cushion(p, m, a, d, l):
    p.rect(235, 270, 765, 740, m, 140)
    p.line([(300, 505), (700, 505)], a, 10)
    p.ell(470, 475, 530, 535, a)
    p.rect(310, 330, 690, 345, _mix(m, l, 0.4), 6)


def jar(p, m, a, d, l):
    p.rect(310, 430, 690, 790, m, 70)
    p.rect(295, 330, 705, 450, a, 28)
    p.rect(355, 520, 645, 700, l, 24)
    p.line([(400, 580), (600, 580)], d, 10)
    p.line([(400, 630), (560, 630)], d, 8)


def lipstick(p, m, a, d, l):
    p.rect(405, 560, 595, 800, d, 20)
    p.rect(420, 440, 580, 570, a, 10)
    p.poly([(440, 440), (560, 440), (560, 290), (500, 215), (440, 290)], m)
    p.poly([(500, 215), (560, 290), (535, 290), (500, 240)], l)


def bottle(p, m, a, d, l):
    p.rect(390, 290, 610, 820, m, 80)
    p.rect(435, 195, 565, 310, d, 22)
    p.rect(420, 150, 580, 215, a, 20)
    p.rect(390, 480, 610, 650, l, 6)
    p.line([(430, 565), (570, 565)], d, 10)


def dumbbell(p, m, a, d, l):
    p.rect(270, 482, 730, 518, d, 14)
    for x0, x1, h in ((180, 250, 140), (255, 320, 100)):
        p.rect(x0, 500 - h, x1, 500 + h, m, 22)
        p.rect(1000 - x1, 500 - h, 1000 - x0, 500 + h, m, 22)
    p.rect(335, 462, 665, 538, a, 18)


def mat(p, m, a, d, l):
    p.rect(230, 380, 780, 660, m, 28)
    p.ell(150, 380, 330, 660, a)
    p.ell(185, 415, 295, 625, m)
    p.ell(220, 455, 260, 585, a)
    p.rect(560, 380, 600, 660, d, 6)
    p.line([(330, 440), (770, 440)], _mix(m, l, 0.3), 8)


def ball(p, m, a, d, l):
    p.ell(240, 240, 760, 760, m)
    layer = Image.new("RGBA", p.img.size, (0, 0, 0, 0))
    q = Pen(layer)
    q.line([(240, 500), (760, 500)], d, 12)
    q.line([(500, 240), (500, 760)], d, 12)
    q.arc(40, 240, 440, 760, 270, 90, d, 12)
    q.arc(560, 240, 960, 760, 90, 270, d, 12)
    mask = Image.new("L", p.img.size, 0)
    ImageDraw.Draw(mask).ellipse([240 * K, 240 * K, 760 * K, 760 * K], fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), mask))
    p.img.alpha_composite(layer)
    p.ell(240, 240, 760, 760, None, d, 12)


def book(p, m, a, d, l):
    p.rect(300, 200, 700, 800, d, 22)
    p.rect(330, 200, 700, 800, m, 18)
    p.rect(690, 215, 722, 785, l, 8)
    p.rect(400, 300, 640, 340, a, 8)
    p.rect(400, 365, 570, 392, a, 6)
    p.ell(480, 560, 620, 700, a)


def notebook(p, m, a, d, l):
    p.rect(310, 210, 700, 800, m, 28)
    p.rect(310, 210, 360, 800, d, 14)
    for y in range(260, 770, 70):
        p.ell(290, y, 345, y + 34, l)
    p.rect(430, 300, 650, 420, l, 12)
    p.line([(450, 340), (620, 340)], d, 8)
    p.line([(450, 380), (580, 380)], d, 8)
    p.rect(430, 680, 650, 700, a, 8)


def pen(p, m, a, d, l):
    p.bar((290, 770), (700, 270), 70, m)
    p.bar((650, 330), (700, 270), 74, a)
    p.poly([(250, 830), (300, 735), (335, 790)], d)
    p.bar((560, 440), (610, 380), 20, l)
    p.bar((705, 265), (760, 200), 36, d)


SHAPES = {f.__name__: f for f in (
    headphones, watch, phone, laptop, speaker, camera, tshirt, shoe, bag, glasses, lamp, mug, plant,
    clock, cushion, jar, lipstick, bottle, dumbbell, mat, ball, book, notebook, pen)}


def render(shape, palette, size=OUT):
    """palette = (bg1, bg2, main, accent, dark, light) as hex strings. Returns JPEG bytes."""
    bg1, bg2, main, accent, dark, light = (_rgb(c) for c in palette)
    img = Image.new("RGB", (SIZE, SIZE), bg1)
    px = ImageDraw.Draw(img)
    for y in range(SIZE):  # vertical gradient
        px.line([(0, y), (SIZE, y)], fill=_mix(bg1, bg2, y / SIZE))
    img = img.convert("RGBA")
    glow = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    ImageDraw.Draw(glow).ellipse([SIZE * 0.12, SIZE * 0.1, SIZE * 0.88, SIZE * 0.86], fill=(255, 255, 255, 90))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(SIZE * 0.04)))
    shade = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shade).ellipse([SIZE * 0.22, SIZE * 0.84, SIZE * 0.78, SIZE * 0.93], fill=(0, 0, 0, 60))
    img = Image.alpha_composite(img, shade.filter(ImageFilter.GaussianBlur(SIZE * 0.02)))
    SHAPES[shape](Pen(img), main, accent, dark, light)
    out = img.convert("RGB").resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=88, optimize=True)
    return buf.getvalue()
