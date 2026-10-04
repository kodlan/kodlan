"""Render ascii/README.md as a two-column DOOM-style SVG card.

usage: python3 ascii/gen_svg.py [ascii/README.md] [profile.svg] [preview.png]
Boxes are rebuilt at COL width from the README's content, so the SVG can be
narrower than the 80-column text version.
"""
import re, html, sys, textwrap

README = sys.argv[1] if len(sys.argv) > 1 else 'ascii/README.md'
OUT    = sys.argv[2] if len(sys.argv) > 2 else 'profile.svg'
COL, GAP = 72, 2
TOTAL = COL * 2 + GAP

# ---- parse README into blocks ----------------------------------------------
raw = [l for l in open(README).read().split('\n') if not l.startswith('```')]
blocks, cur = [], []
for l in raw:
    if l.strip() == '':
        if cur: blocks.append(cur); cur = []
    else:
        cur.append(l)
if cur: blocks.append(cur)
name, _loc, hangar, campaign, arsenal, targets, status, linkedin = blocks

def inner(rows):
    """content rows of a box, without borders and side padding"""
    return [l[1:-1].strip() for l in rows if not set(l) <= set('+-=')]

# ---- box builders at COL width ---------------------------------------------
HR = '+' + '=' * (COL - 2) + '+'
def row(txt=''): return ('|  ' + txt).ljust(COL - 1) + '|'
def box(header, body, spacer=False):
    out = [HR, row(header), HR]
    if spacer: out.append(row())
    out += [row(t) for t in body]
    if spacer: out.append(row())
    return out + [HR]

h = inner(hangar)
head = re.split(r'\s{3,}', h[0])                         # "E1M1: HANGAR", "KNEE-DEEP IN THE CODE"
hdr = head[0] + ' ' * (COL - 6 - len(head[0]) - len(head[1])) + head[1]
paras, cur = [], []
for t in h[1:]:
    if t == '':
        if cur: paras.append(' '.join(cur)); cur = []
    else: cur.append(t)
if cur: paras.append(' '.join(cur))
hbody = []
for ptxt in paras: hbody += textwrap.wrap(ptxt, COL - 6) + ['']
hangar_b = box(hdr, hbody[:-1], spacer=True)

def leader_rows(rows):
    """'E4  Google ..... Title' -> re-dot so values align, at minimum width"""
    parsed = [re.match(r'(\S+\s+)(.*?)\s*\.{2,}\s*(.*)', t).groups() for t in rows]
    w = max(len(p[1]) for p in parsed)
    return [f'{p[0]}{p[1]} {"." * (w - len(p[1]) + 2)} {p[2]}' for p in parsed]

c = inner(campaign); campaign_b = box(c[0], leader_rows(c[1:]))
a = inner(arsenal);  arsenal_b  = box(a[0], leader_rows(a[1:]))
t = inner(targets);  targets_b  = box(t[0], [x for x in t[1:] if x], spacer=True)

# status bar: AMMO | HEALTH | ARMS | ARMOR | KEYS, then the cheat row
s = inner(status)
cells = [[x.strip() for x in l.strip('|').split('|')] for l in s[:2]]
cheat = s[2]
widths = [9, 9, 0, 9, 11]
widths[2] = COL - 2 - sum(widths) - 4
sep = '+' + '+'.join('-' * w for w in widths) + '+'
def srow(vals): return '|' + '|'.join(v.center(w) for v, w in zip(vals, widths)) + '|'
status_b = [sep, srow(cells[0]), srow(cells[1]), sep, '|' + cheat.center(COL - 2) + '|', '+' + '-' * (COL - 2) + '+']

# ---- compose two columns ---------------------------------------------------
blank = ' ' * COL
left  = hangar_b + [blank] + targets_b
right = campaign_b + [blank] + arsenal_b + [blank] + status_b
diff = len(right) - len(left)
if diff > 0:   # pad TARGETS content with blank rows at the bottom, inside the box
    targets_b = targets_b[:-1] + [row()] * diff + targets_b[-1:]
    left = hangar_b + [blank] + targets_b
elif diff < 0:
    right += [blank] * (-diff)
body = [l.ljust(COL) + ' ' * GAP + r.ljust(COL) for l, r in zip(left, right)]

namew = max(len(l) for l in name[:4]); off = max(0, (TOTAL - namew) // 2)
url = re.search(r'https?://\S+', linkedin[0]).group()
meta = ('Warsaw, Poland    //    ' + url).center(TOTAL)
lines = [' ' * off + l for l in name[:4]] + [meta, ''] + body
lines = [l.rstrip() for l in lines]
kind  = ['name'] * 4 + ['link', ''] + ['body'] * len(body)

# ---- colouring --------------------------------------------------------------
C = dict(bg='#0c0c0c', red='#e3261a', orange='#f0922b', green='#4ec94e', yellow='#f2c21b',
         blue='#3c7bea', cyan='#5ec8d8', gray='#7a7a7a', text='#c9c0a8', dim='#9a9a9a', link='#5aa0ff')
HEADERS = ['E1M1: HANGAR', 'KNEE-DEEP IN THE CODE', 'CAMPAIGN', 'ARSENAL', 'CURRENT TARGETS']

def tokens(line, k):
    if k == 'name': return [(line, C['orange'])]
    if k == 'link':
        m = re.search(r'https?://\S+', line)
        return [(line[:m.start()], C['dim']), (m.group(), C['link']), (line[m.end():], C['dim'])]
    pats = [(re.escape(h), C['orange']) for h in HEADERS]
    pats += [(r'(?<=E[1-4]  )[A-Za-z ]+?(?=,| \.)|(?<=\[[2-7]\] )[A-Z0-9 ]+?(?= \.)|(?<=, )[A-Za-z]+(?= \.)', C['green']),
             (r'\bE[1-4]\b', C['yellow']), (r'\[[2-7]\]', C['yellow']),
             (r'\[B\]', C['blue']), (r'\[Y\]', C['yellow']), (r'\[R\]', C['red']),
             (r'\b999\b|\b100%|\b200%', C['orange']),
             (r'COFFEE: FULL|BUILD: GREEN|IDDQD: ON|IDKFA: ON', C['orange']),
             (r'AMMO|HEALTH|ARMS|ARMOR|KEYS', C['dim']),
             (r'[+=|\-]+', C['gray']), (r'\.{2,}', C['gray']), (r'>', C['red'])]
    rx = re.compile('|'.join(f'(?P<g{n}>{p})' for n, (p, _) in enumerate(pats)))
    segs, i = [], 0
    for m in rx.finditer(line):
        if m.start() > i: segs.append((line[i:m.start()], C['text']))
        segs.append((m.group(), pats[int(m.lastgroup[1:])][1])); i = m.end()
    if i < len(line): segs.append((line[i:], C['text']))
    if re.match(r'\|  > ', line):   # target rows: text in cyan
        segs = [(t, C['cyan'] if c == C['text'] and t.strip() else c) for t, c in segs]
    return segs

# ---- emit SVG ---------------------------------------------------------------
FS = 13; CW = FS * 0.6; LH = FS * 1.32; PAD = 16
W = round(PAD * 2 + TOTAL * CW); H = round(PAD * 2 + len(lines) * LH)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
       f'font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, \'DejaVu Sans Mono\', \'Courier New\', monospace" font-size="{FS}px">',
       f'<rect width="100%" height="100%" rx="6" fill="{C["bg"]}"/>']
rows = []
for idx, (line, k) in enumerate(zip(lines, kind)):
    segs = tokens(line, k) if line else []; rows.append(segs)
    if not line: continue
    inner_svg = ''.join(f'<tspan fill="{c}">{html.escape(t)}</tspan>' for t, c in segs)
    if k == 'link': inner_svg = f'<a href="{url}">{inner_svg}</a>'
    svg.append(f'<text x="{PAD}" y="{PAD + FS + idx * LH:.1f}" xml:space="preserve" '
               f'textLength="{len(line) * CW:.1f}" lengthAdjust="spacing">{inner_svg}</text>')
svg.append('</svg>')
open(OUT, 'w').write('\n'.join(svg) + '\n')

# ---- optional PNG preview ---------------------------------------------------
if len(sys.argv) > 3:
    import glob
    from PIL import Image, ImageDraw, ImageFont
    ttf = (glob.glob('/usr/share/fonts/**/DejaVuSansMono.ttf', recursive=True)
           or glob.glob('/home/*/.cache/**/DejaVuSansMono.ttf', recursive=True))[0]
    font = ImageFont.truetype(ttf, 14); cw = font.getlength('M'); lh = 19; pad = 16
    im = Image.new('RGB', (int(pad * 2 + TOTAL * cw), int(pad * 2 + len(lines) * lh)), C['bg'])
    d = ImageDraw.Draw(im)
    for idx, segs in enumerate(rows):
        x = pad
        for t, c in segs: d.text((x, pad + idx * lh), t, fill=c, font=font); x += len(t) * cw
    im.save(sys.argv[3])
print(f'svg {W}x{H}, {len(lines)} lines, {TOTAL} cols')
