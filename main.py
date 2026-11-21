#!/usr/bin/env python3
"""The Passport Page of a Country That Isn't There.

An invented passport spread for the island Republic of Tavara: a data
page (portrait, personal data, machine-readable zone) on the left and a
visa/stamps page on the right. Pure Python 3.13 standard library,
deterministic (two runs are byte-identical), no network.

Writes entry.png, 1024x1024, under 1 MiB.
"""

import math
import os
import struct
import zlib

W = H = 1024

# ---------------------------------------------------------------- palette
PAPER = (239, 230, 207)
PAPER_DARK = (228, 216, 188)
INK = (30, 42, 68)          # dark navy document ink
INK_SOFT = (58, 70, 96)
GOLD = (176, 141, 62)
GOLD_LT = (203, 172, 96)
TEAL = (46, 98, 110)
PHOTO_BG = (176, 190, 198)
SKIN = (232, 184, 141)
SKIN_DK = (214, 164, 122)
HAIR = (58, 38, 28)
JACKET = (38, 52, 78)
SHIRT = (244, 244, 238)
RED = (158, 44, 38)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w=W, h=H, bg=PAPER):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(bg) * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def blend(self, x, y, c, a):
        """Blend colour c over pixel (x, y) with alpha a (0..255)."""
        if 0 <= x < self.w and 0 <= y < self.h and a > 0:
            i = (y * self.w + x) * 3
            self.px[i] = (c[0] * a + self.px[i] * (255 - a)) // 255
            self.px[i + 1] = (c[1] * a + self.px[i + 1] * (255 - a)) // 255
            self.px[i + 2] = (c[2] * a + self.px[i + 2] * (255 - a)) // 255

    def rect(self, x0, y0, x1, y1, c):
        x0 = max(0, x0)
        y0 = max(0, y0)
        x1 = min(self.w, x1)
        y1 = min(self.h, y1)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for y in range(y0, y1):
            i = (y * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x0, x1, y, c, t=1):
        self.rect(x0, y, x1, y + t, c)

    def vline(self, x, y0, y1, c, t=1):
        self.rect(x, y0, x + t, y1, c)

    def line(self, x0, y0, x1, y1, c):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def ellipse(self, cx, cy, rx, ry, c):
        """Filled ellipse."""
        for dy in range(-ry, ry + 1):
            t = 1.0 - (dy * dy) / float(ry * ry)
            if t < 0:
                continue
            hw = int(rx * math.sqrt(t))
            self.rect(cx - hw, cy + dy, cx + hw + 1, cy + dy + 1, c)

    def circle_outline(self, cx, cy, r, c, t=1):
        for k in range(360):
            a = math.radians(k)
            for d in range(t):
                self.set(int(cx + (r + d) * math.cos(a)),
                         int(cy + (r + d) * math.sin(a)), c)

    def ellipse_outline(self, cx, cy, rx, ry, c, t=1):
        for k in range(720):
            a = math.radians(k * 0.5)
            for d in range(t):
                self.set(int(cx + (rx + d) * math.cos(a)),
                         int(cy + (ry + d) * math.sin(a)), c)


def png_bytes(cv):
    """Encode the canvas as PNG (RGB, 8-bit), picking the smaller of
    filter-0 and filter-Up IDAT streams. Deterministic."""
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw0 = bytearray()
    rawu = bytearray()
    prev = bytes(cv.w * 3)
    for y in range(cv.h):
        row = bytes(cv.px[y * cv.w * 3:(y + 1) * cv.w * 3])
        raw0.append(0)
        raw0 += row
        rawu.append(2)
        rawu += bytes((b - p) & 0xFF for b, p in zip(row, prev))
        prev = row
    idat0 = zlib.compress(bytes(raw0), 9)
    idatu = zlib.compress(bytes(rawu), 9)
    idat = idat0 if len(idat0) <= len(idatu) else idatu
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


# ------------------------------------------------------- 5x7 pixel font
# Each glyph: 7 rows of 5 cells, '#' = ink, '.' = empty.
FONT = {
    "A": ("..#..", ".#.#.", "#...#", "#...#", "#####", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
}

FONT.update({
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "(": ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "&": (".###.", "#...#", "#...#", ".#...", "#.#.#", "#..#.", ".##.#"),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "*": (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    ";": (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.##.", "#..##"),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
})


def text_w(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color, alpha=255):
    """Draw uppercase text (chars outside the font are skipped)."""
    cx = x
    for ch in s.upper():
        g = FONT.get(ch)
        if g is None:
            cx += 6 * scale
            continue
        for r in range(7):
            row = g[r]
            for cix in range(5):
                if row[cix] == "#":
                    px = cx + cix * scale
                    py = y + r * scale
                    if alpha >= 255:
                        cv.rect(px, py, px + scale, py + scale, color)
                    else:
                        for yy in range(py, py + scale):
                            for xx in range(px, px + scale):
                                cv.blend(xx, yy, color, alpha)
        cx += 6 * scale
    return cx


def draw_text_c(cv, cx, y, s, scale, color, alpha=255):
    draw_text(cv, cx - text_w(s, scale) // 2, y, s, scale, color, alpha)


# ------------------------------------------------------------- guilloche
def guilloche(cv, x0, x1, y0, y1, color, step=9, amp=3, alpha=70):
    """Fine wavy security lines across a region."""
    y = y0
    ph = 0.0
    while y < y1:
        prev = None
        for x in range(x0, x1, 2):
            yy = int(y + amp * math.sin(x / 34.0 + ph))
            if prev is not None:
                # thin line via direct blends
                for xx in range(prev[0], x + 1):
                    t = prev[1] + (yy - prev[1]) * (xx - prev[0]) / 2.0
                    cv.blend(xx, int(t), color, alpha)
            prev = (x, yy)
        y += step
        ph += 0.7


def speckle(cv, seed, n, x0, x1, y0, y1, color, alpha=26):
    """Deterministic paper speckle (LCG, fixed seed)."""
    s = seed
    for _ in range(n):
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        x = x0 + s % (x1 - x0)
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        y = y0 + s % (y1 - y0)
        cv.blend(x, y, color, alpha)


# -------------------------------------------------------------- emblem
def emblem(cv, cx, cy, r, color):
    """Tavara crest: a ring, a lighthouse with rays, waves below."""
    cv.circle_outline(cx, cy, r, color, 2)
    cv.circle_outline(cx, cy, r - 5, color, 1)
    # lighthouse tower
    cv.rect(cx - 4, cy - r + 12, cx + 5, cy + 6, color)
    cv.rect(cx - 6, cy - r + 8, cx + 7, cy - r + 12, color)
    cv.rect(cx - 7, cy + 6, cx + 8, cy + 8, color)
    # light rays
    cv.line(cx - 6, cy - r + 9, cx - r + 4, cy - r + 16, color)
    cv.line(cx + 6, cy - r + 9, cx + r - 4, cy - r + 16, color)
    cv.line(cx, cy - r + 7, cx, cy - r + 2, color)
    # star above the lamp
    cv.set(cx, cy - r + 4, color)
    # waves
    for k, wy in enumerate((cy + 12, cy + 18)):
        for x in range(cx - r + 8, cx + r - 7):
            yy = wy + int(2 * math.sin((x - cx) / 6.0 + k * 1.7))
            cv.set(x, yy, color)


# ------------------------------------------------------------- portrait
def portrait(cv, x0, y0, x1, y1):
    """Flat-style passport portrait: a Tavaran woman, head and shoulders.
    Drawn procedurally; reads clearly even at 300 px."""
    cv.rect(x0, y0, x1, y1, PHOTO_BG)
    # soft vertical light
    for yy in range(y0, y1):
        a = 18 if (yy - y0) % 2 == 0 else 0
        for xx in range(x0, x1, 7):
            cv.blend(xx, yy, (255, 255, 255), a)
    w = x1 - x0
    h = y1 - y0
    cx = (x0 + x1) // 2
    # shoulders / jacket (kept inside the photo frame)
    cv.ellipse(cx, y1 - 40, w // 2 + 6, 40, JACKET)
    cv.rect(x0, y1 - 52, x1, y1, JACKET)
    # white shirt V
    for i in range(26):
        cv.line(cx - i, y1 - 62 + i, cx + i, y1 - 62 + i, SHIRT)
    # neck
    cv.rect(cx - 13, y0 + 108, cx + 14, y0 + 138, SKIN_DK)
    cv.rect(cx - 13, y0 + 108, cx + 14, y0 + 116, SKIN)
    # hair back (bob)
    cv.ellipse(cx, y0 + 62, 52, 62, HAIR)
    # face
    cv.ellipse(cx, y0 + 66, 38, 48, SKIN)
    # hair fringe + side locks
    cv.ellipse(cx, y0 + 34, 40, 26, HAIR)
    cv.ellipse(cx - 34, y0 + 78, 12, 40, HAIR)
    cv.ellipse(cx + 34, y0 + 78, 12, 40, HAIR)
    # ears
    cv.ellipse(cx - 38, y0 + 70, 6, 10, SKIN)
    cv.ellipse(cx + 38, y0 + 70, 6, 10, SKIN)
    # brows
    cv.rect(cx - 24, y0 + 56, cx - 8, y0 + 59, HAIR)
    cv.rect(cx + 8, y0 + 56, cx + 25, y0 + 59, HAIR)
    # eyes
    cv.ellipse(cx - 16, y0 + 66, 5, 4, (255, 255, 255))
    cv.ellipse(cx + 16, y0 + 66, 5, 4, (255, 255, 255))
    cv.ellipse(cx - 16, y0 + 66, 3, 3, (28, 22, 18))
    cv.ellipse(cx + 16, y0 + 66, 3, 3, (28, 22, 18))
    # nose
    cv.line(cx, y0 + 68, cx - 2, y0 + 82, SKIN_DK)
    cv.line(cx - 2, y0 + 82, cx + 2, y0 + 82, SKIN_DK)
    # lips
    cv.rect(cx - 9, y0 + 94, cx + 10, y0 + 97, (178, 92, 82))
    # jacket lapels
    cv.line(cx - 14, y1 - 60, cx - 34, y1 - 8, (24, 34, 56))
    cv.line(cx + 14, y1 - 60, cx + 34, y1 - 8, (24, 34, 56))
    # frame
    cv.rect(x0, y0, x1, y0 + 2, INK)
    cv.rect(x0, y1 - 2, x1, y1, INK)
    cv.rect(x0, y0, x0 + 2, y1, INK)
    cv.rect(x1 - 2, y0, x1, y1, INK)


# ---------------------------------------------------------------- stamps
MAGENTA = (255, 0, 255)


def make_stamp(lines, ink, w=210, h=112):
    """A small stamp layer; magenta is transparent when blitted."""
    s = Canvas(w, h, MAGENTA)
    s.rect(4, 4, w - 4, h - 4, ink)
    s.rect(7, 7, w - 7, h - 7, ink)
    # clear the inside back to magenta so only the frame + text show
    s.rect(8, 8, w - 8, h - 8, MAGENTA)
    s.rect(4, 4, w - 4, 5, ink)
    s.rect(4, h - 5, w - 4, h - 4, ink)
    s.rect(4, 4, 5, h - 4, ink)
    s.rect(w - 5, 4, w - 4, h - 4, ink)
    y = 16
    for txt, sc in lines:
        draw_text_c(s, w // 2, y, txt, sc, ink)
        y += 9 * sc + 6
    return s


def blit_rotated(dst, src, cx, cy, angle_deg, alpha=200):
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    hw, hh = src.w // 2, src.h // 2
    for dy in range(-hh, hh):
        for dx in range(-hw, hw):
            sx = int(dx * ca + dy * sa) + hw
            sy = int(-dx * sa + dy * ca) + hh
            if 0 <= sx < src.w and 0 <= sy < src.h:
                i = (sy * src.w + sx) * 3
                r, g, b = src.px[i], src.px[i + 1], src.px[i + 2]
                if (r, g, b) != MAGENTA:
                    dst.blend(cx + dx, cy + dy, (r, g, b), alpha)


def round_stamp(dst, cx, cy, r, ink, words, angle=-8, alpha=190):
    """Circular fee stamp, drawn rotated as a whole."""
    s = Canvas(2 * r + 8, 2 * r + 8, MAGENTA)
    cc = r + 4
    s.circle_outline(cc, cc, r, ink, 2)
    s.circle_outline(cc, cc, r - 6, ink, 1)
    for k in range(0, 360, 12):
        a = math.radians(k)
        s.set(int(cc + (r - 3) * math.cos(a)),
              int(cc + (r - 3) * math.sin(a)), ink)
    y = cc - 10 * len(words) // 2
    for wd in words:
        draw_text_c(s, cc, y, wd, 1, ink)
        y += 12
    blit_rotated(dst, s, cx, cy, angle, alpha)


# ------------------------------------------------------------------- MRZ
def mrz_check(s):
    vals = {}
    for i in range(10):
        vals[str(i)] = i
    for i in range(26):
        vals[chr(65 + i)] = 10 + i
    vals["<"] = 0
    w = (7, 3, 1)
    return str(sum(vals[ch] * w[i % 3] for i, ch in enumerate(s)) % 10)


def mrz_lines():
    line1 = "P<TVAVARKAS<<MIRA<SOLENNE"
    line1 = line1 + "<" * (44 - len(line1))
    doc = "TV2048817"
    dob = "940314"
    exp = "360211"
    pers = "<" * 14
    l2 = (doc + mrz_check(doc) + "TVA" + dob + mrz_check(dob) + "F"
          + exp + mrz_check(exp) + pers)
    l2 = l2 + mrz_check(pers)
    comp = (doc + mrz_check(doc) + dob + mrz_check(dob)
            + exp + mrz_check(exp) + pers + mrz_check(pers))
    l2 = l2 + mrz_check(comp)
    return line1, l2


def draw_mrz(cv, x, y, s):
    """MRZ at scale 2, zero letter gap: 44 chars fit the data page."""
    cx = x
    for ch in s:
        g = FONT.get(ch)
        if g:
            for r in range(7):
                for cix in range(5):
                    if g[r][cix] == "#":
                        cv.rect(cx + cix * 2, y + r * 2,
                                cx + cix * 2 + 2, y + r * 2 + 2, INK)
        cx += 10


# ------------------------------------------------------------- signature
def signature(cv, x0, y, x1):
    """A flowing bearer signature, deterministic."""
    pts = []
    x = x0
    while x <= x1:
        pts.append((x, y + int(6 * math.sin((x - x0) / 9.0))
                    - int(4 * math.sin((x - x0) / 4.3))))
        x += 2
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        cv.line(ax, ay, bx, by, INK)
    cv.line(x0 + 8, y - 14, x0 + 26, y + 2, INK)
    cv.line(x0 + 26, y + 2, x0 + 44, y - 10, INK)


# ------------------------------------------------------------ the spread
def field(cv, x, y, label, value, vscale=2, lw=170):
    draw_text(cv, x, y, label, 1, INK_SOFT)
    draw_text(cv, x, y + 10, value, vscale, INK)
    return y + 12 + 8 * vscale + 8


def build():
    cv = Canvas()
    # --- paper, security print, speckle
    guilloche(cv, 40, 984, 50, 980, TEAL, step=10, amp=3, alpha=46)
    guilloche(cv, 40, 984, 50, 980, GOLD, step=23, amp=4, alpha=26)
    speckle(cv, 20261121, 2600, 40, 984, 50, 980, (120, 100, 60), 22)
    speckle(cv, 777, 1400, 40, 984, 50, 980, (255, 255, 255), 20)
    # --- spread frame + gutter
    cv.rect(28, 28, 996, 32, INK)
    cv.rect(28, 988, 996, 992, INK)
    cv.rect(28, 28, 32, 992, INK)
    cv.rect(992, 28, 996, 992, INK)
    cv.rect(40, 40, 984, 42, GOLD)
    cv.rect(40, 978, 984, 980, GOLD)
    for gx in range(505, 520):
        cv.blend(gx, 0, (0, 0, 0), 0)  # gutter shading below
    for y in range(40, 980):
        cv.blend(508, y, (90, 80, 60), 60)
        cv.blend(509, y, (90, 80, 60), 90)
        cv.blend(510, y, (90, 80, 60), 110)
        cv.blend(511, y, (90, 80, 60), 90)
        cv.blend(512, y, (90, 80, 60), 60)
    cv.vline(500, 40, 980, INK_SOFT, 1)

    # ======================================================= LEFT: data
    emblem(cv, 276, 106, 30, TEAL)
    draw_text_c(cv, 276, 148, "REPUBLIKA TAVARA", 2, INK)
    draw_text_c(cv, 276, 168, "PASAPORTA  -  PASSPORT", 1, GOLD)
    cv.hline(90, 462, 190, GOLD, 2)

    portrait(cv, 70, 212, 226, 402)
    # gold seal overlapping the photo corner
    cv.circle_outline(216, 388, 26, GOLD, 2)
    cv.circle_outline(216, 388, 21, GOLD, 1)
    draw_text_c(cv, 216, 380, "TAVARA", 1, GOLD)
    draw_text_c(cv, 216, 392, "2026", 1, GOLD)

    y = 214
    y = field(cv, 246, y, "SURNAME / PREZIME", "VARKAS")
    y = field(cv, 246, y, "GIVEN NAMES / IMENA", "MIRA SOLENNE")
    y = field(cv, 246, y, "NATIONALITY / DRZAVLJANSTVO", "TAVARAN")
    y = field(cv, 246, y, "DATE OF BIRTH / RODJENJE", "14 MAR 1994")
    y = field(cv, 246, y, "PLACE OF BIRTH / RODNO MJESTO", "PORT LIORA")
    field(cv, 246, y, "SEX / SPOL", "F")

    y = 452
    y = field(cv, 70, y, "DATE OF ISSUE / IZDAVANJE", "12 FEB 2026")
    y = field(cv, 70, y, "AUTHORITY / IZDAVATELJ", "PORT LIORA")
    field(cv, 290, 452, "DATE OF EXPIRY / VRIJEDI DO", "11 FEB 2036")
    field(cv, 290, 512, "PASSPORT NO. / BROJ", "TV-2048817")

    draw_text(cv, 70, 620, "SIGNATURE OF BEARER / POTPIS", 1, INK_SOFT)
    signature(cv, 70, 660, 330)
    cv.hline(70, 330, 668, INK, 1)
    draw_text(cv, 70, 690, "HOLDER IS A CITIZEN OF THE", 1, INK_SOFT)
    draw_text(cv, 70, 702, "REPUBLIC OF TAVARA.", 1, INK_SOFT)
    draw_text(cv, 70, 726, "THIS PASSPORT REMAINS THE", 1, INK_SOFT)
    draw_text(cv, 70, 738, "PROPERTY OF THE REPUBLIC.", 1, INK_SOFT)

    # MRZ
    cv.hline(56, 496, 852, INK, 2)
    l1, l2 = mrz_lines()
    draw_mrz(cv, 56, 872, l1)
    draw_mrz(cv, 56, 894, l2)
    draw_text(cv, 56, 930, "P<TVA VARKAS - TV2048817 - PORT LIORA", 1, INK_SOFT)

    # ====================================================== RIGHT: visas
    draw_text_c(cv, 754, 62, "VIZAT  -  VISAS", 2, INK)
    draw_text(cv, 900, 66, "PAGE 12", 1, INK_SOFT)
    cv.hline(556, 952, 92, GOLD, 2)
    # faint watermark emblem (low alpha so stamps stay readable)
    for k in range(360):
        a = math.radians(k)
        cv.blend(int(754 + 120 * math.cos(a)),
                 int(300 + 120 * math.sin(a)), TEAL, 46)
    for k in range(0, 360, 30):
        a = math.radians(k)
        for t in range(0, 118, 2):
            cv.blend(int(754 + t * math.cos(a)),
                     int(300 + t * math.sin(a)), TEAL, 20)

    st1 = make_stamp([("DRESHKA", 2), ("ENTRY", 1), ("03 MAR 2026", 2),
                      ("HARBOUR GATE 2", 1)], (40, 80, 150))
    blit_rotated(cv, st1, 660, 180, -6)
    st2 = make_stamp([("DRESHKA", 2), ("EXIT", 1), ("17 MAR 2026", 2),
                      ("HARBOUR GATE 2", 1)], (150, 60, 45))
    blit_rotated(cv, st2, 872, 186, 5)
    st3 = make_stamp([("CORVAIN", 2), ("ENTRY", 1), ("02 JUN 2026", 2),
                      ("FERRY TERMINAL", 1)], (110, 70, 140))
    blit_rotated(cv, st3, 664, 330, 4)
    st4 = make_stamp([("HALBRECHT", 2), ("DEPARTURE", 1), ("19 SEP 2026", 2),
                      ("NORTH PIER", 1)], (40, 110, 90))
    blit_rotated(cv, st4, 872, 336, -4)

    # --- Dreshka visa box
    cv.rect(556, 452, 952, 454, INK)
    cv.rect(556, 452, 558, 742, INK)
    cv.rect(950, 452, 952, 742, INK)
    cv.rect(556, 740, 952, 742, INK)
    cv.rect(556, 452, 952, 486, TEAL)
    draw_text(cv, 570, 464, "VISA  -  DRESHKA", 2, (255, 255, 255))
    draw_text(cv, 830, 466, "NO. DR-11804", 1, (255, 255, 255))
    yy = 506
    for lab, val in (("TYPE", "C - MULTIPLE ENTRY"),
                     ("ISSUED", "24 FEB 2026 - PORT LIORA"),
                     ("VALID", "90 DAYS - SINGLE STAY 30 DAYS"),
                     ("CONDITION", "REGISTER WITH THE"),
                     ("", "HARBOURMASTER WITHIN"),
                     ("", "48 HOURS OF LANDING"),
                     ("FEE", "12 TVD - PAID")):
        draw_text(cv, 570, yy, lab, 1, INK_SOFT)
        draw_text(cv, 700, yy, val, 1, INK)
        yy += 20
    cv.hline(570, 938, 700, GOLD, 1)
    draw_text(cv, 570, 712, "MARITIME CODE SEC. 12 APPLIES.", 1, INK_SOFT)

    round_stamp(cv, 884, 700, 40, (150, 60, 45),
                ("FEE", "PAID", "12 TVD"), angle=-10)

    # --- harbourmaster's note: the telling paperwork detail
    cv.hline(556, 952, 772, INK, 2)
    draw_text(cv, 556, 792, "HARBOURMASTER'S NOTE", 2, INK)
    draw_text(cv, 556, 822, "ALL ARRIVALS BY SEA MUST PRESENT THIS", 1, INK)
    draw_text(cv, 556, 838, "PASSPORT TO THE HARBOURMASTER OF", 1, INK)
    draw_text(cv, 556, 854, "PORT LIORA WITHIN 48 HOURS. VESSELS", 1, INK)
    draw_text(cv, 556, 870, "UNDER 12 M REPORT TO THE NORTH PIER", 1, INK)
    draw_text(cv, 556, 886, "BEFORE UNLOADING. - MARITIME CODE", 1, INK)
    draw_text(cv, 556, 902, "SEC. 12, REPUBLIC OF TAVARA.", 1, INK)
    # small anchor doodle
    ax, ay = 920, 850
    cv.circle_outline(ax, ay - 18, 8, TEAL, 2)
    cv.vline(ax, ay - 26, ay + 22, TEAL, 2)
    cv.line(ax - 14, ay - 8, ax + 14, ay - 8, TEAL)
    cv.line(ax - 14, ay - 8, ax - 12, ay + 8, TEAL)
    cv.line(ax + 14, ay - 8, ax + 12, ay + 8, TEAL)
    cv.line(ax - 12, ay + 8, ax + 12, ay + 8, TEAL)
    draw_text(cv, 556, 940, "TAVARA - ISLAND REPUBLIC - EST. 1962", 1, GOLD)
    return cv


def main():
    cv = build()
    data = png_bytes(cv)
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, "entry.png")
        with open(path, "wb") as f:
            f.write(data)
    except OSError:
        os.makedirs("out", exist_ok=True)
        path = os.path.join("out", "entry.png")
        with open(path, "wb") as f:
            f.write(data)
    import hashlib
    print("wrote %s %d bytes sha256=%s" % (path, len(data),
                                           hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
