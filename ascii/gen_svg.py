import re, html, sys
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    pass

# usage: python3 ascii/gen_svg.py [ascii/README.md] [profile.svg] [preview.png]
README=sys.argv[1] if len(sys.argv)>1 else 'ascii/README.md'
OUT=sys.argv[2] if len(sys.argv)>2 else 'profile.svg'
raw=[l for l in open(README).read().split('\n') if not l.startswith('```')]
# split into blocks separated by blank lines
blocks=[]; cur=[]
for l in raw:
    if l.strip()=='':
        if cur: blocks.append(cur); cur=[]
    else: cur.append(l)
if cur: blocks.append(cur)
name, _warsaw, hangar, campaign, arsenal, targets, status, linkedin = blocks
COL=80; GAP=2; TOTAL=COL*2+GAP
import textwrap
def rewrap_hangar(b, width=62):
    """same text, wrapped narrower so both paragraphs take 4 lines"""
    top, head, sep = b[0], b[1], b[2]
    inner=[l[1:-1].strip() for l in b[3:-1]]
    paras=[]; cur=[]
    for l in inner:
        if l=='' :
            if cur: paras.append(' '.join(cur)); cur=[]
        else: cur.append(l)
    if cur: paras.append(' '.join(cur))
    out=[top, head, sep, '|'+' '*(COL-2)+'|']
    for i,ptxt in enumerate(paras):
        for l in textwrap.wrap(ptxt, width): out.append(('|  '+l).ljust(COL-1)+'|')
        out.append('|'+' '*(COL-2)+'|')
    out.append(b[-1]); return out
hangar=rewrap_hangar(hangar)
blank='|'+' '*(COL-2)+'|'
targets=targets[:3]+[blank]+targets[3:-1]+[blank]+targets[-1:]   # spacer rows so columns match

# widen the 78-col status bar to 80 by growing the ARMS column / bottom row
def widen(l):
    if len(l)!=78: return l
    if l[53]=='|' or l[53]=='+': return l[:53]+(l[52]*2)+l[53:]   # grow the ARMS column
    if set(l[1:-1])=={'-'}: return '+'+'-'*78+'+'
    return '|'+l[1:-1].strip().center(78)+'|'                      # full-width cheat row
status=[widen(l) for l in status]
def pad(b): return [l.ljust(COL) for l in b]
left = pad(hangar) + [' '*COL] + pad(targets)
right= pad(campaign) + [' '*COL] + pad(arsenal) + [' '*COL] + pad(status)
assert len(left)==len(right), (len(left),len(right))
body=[l+' '*GAP+r for l,r in zip(left,right)]
namew=max(len(l) for l in name[:4]); off=(TOTAL-namew)//2
url=re.search(r'https?://\S+', linkedin[0]).group()
meta=('Warsaw, Poland    //    '+url).center(TOTAL).rstrip()
lines=[(' '*off+l) for l in name[:4]] + [meta] + [''] + body
lines=[l.rstrip() for l in lines]
kind=['name']*4+['link','']+['body']*len(body)

C=dict(bg='#0c0c0c', red='#e3261a', orange='#f0922b', green='#4ec94e', yellow='#f2c21b', blue='#3c7bea', cyan='#5ec8d8',
       gray='#7a7a7a', text='#c9c0a8', dim='#9a9a9a', link='#5aa0ff')
HEADERS=['E1M1: HANGAR','KNEE-DEEP IN THE CODE','CAMPAIGN','ARSENAL','CURRENT TARGETS']
LABELS=['PISTOL','SHOTGUN','CHAINGUN','ROCKET LAUNCHER','PLASMA RIFLE','BFG 9000',
        'Google','Dell Technologies','Oracle','Conscensia','SoftServe']

def tokens(line, k):
    if k=='name': return [(line, C['orange'])]
    if k=='dim': return [(line, C['dim'])]
    if k=='link':
        m=re.search(r'https?://\S+', line)
        return [(line[:m.start()], C['dim']), (m.group(), C['link']), (line[m.end():], C['dim'])]
    pats=[(re.escape(h), C['orange']) for h in HEADERS]
    # green labels only on campaign / arsenal rows (right or left column)
    for w in LABELS: pats.append((r'(?<=E[1-4]  )'+re.escape(w)+r'|(?<=, )'+re.escape(w)+r'(?= \.)|(?<=\[[2-7]\] )'+re.escape(w), C['green']))
    pats += [(r'\bE[1-4]\b', C['yellow']), (r'\[[2-7]\]', C['yellow']),
             (r'\[B\]', C['blue']), (r'\[Y\]', C['yellow']), (r'\[R\]', C['red']),
             (r'\b999\b|\b100%|\b200%', C['orange']),
             (r'COFFEE: FULL|BUILD: GREEN|IDDQD: ON|IDKFA: ON', C['orange']),
             (r'AMMO|HEALTH|ARMS|ARMOR|KEYS', C['dim']),
             (r'[+=|\-]+', C['gray']), (r'\.{2,}', C['gray']), (r'>', C['red'])]
    rx=re.compile('|'.join(f'(?P<g{n}>{p})' for n,(p,_) in enumerate(pats)))
    segs=[]; i=0
    for m in rx.finditer(line):
        if m.start()>i: segs.append((line[i:m.start()], C['text']))
        segs.append((m.group(), pats[int(m.lastgroup[1:])][1])); i=m.end()
    if i<len(line): segs.append((line[i:], C['text']))
    # target rows: body text after the red chevron in green
    if re.match(r'\|  > ', line):
        segs=[(t, C['cyan'] if c==C['text'] and t.strip() and not t.strip().startswith('|') else c) for t,c in segs]
    return segs

FS=13; CW=FS*0.6; LH=FS*1.32; PAD=16
W=round(PAD*2+TOTAL*CW); H=round(PAD*2+len(lines)*LH)
svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, \'DejaVu Sans Mono\', \'Courier New\', monospace" font-size="{FS}px">',
     f'<rect width="100%" height="100%" rx="6" fill="{C["bg"]}"/>']
rows=[]
for idx,(line,k) in enumerate(zip(lines,kind)):
    segs=tokens(line,k) if line else []; rows.append(segs)
    if not line: continue
    inner=''.join(f'<tspan fill="{c}">{html.escape(t)}</tspan>' for t,c in segs)
    if k=='link': inner=f'<a href="https://www.linkedin.com/in/stanislavbardyuk/">{inner}</a>'
    svg.append(f'<text x="{PAD}" y="{PAD+FS+idx*LH:.1f}" xml:space="preserve" textLength="{len(line)*CW:.1f}" lengthAdjust="spacing">{inner}</text>')
svg.append('</svg>')
open(OUT,'w').write('\n'.join(svg)+'\n')

if len(sys.argv)>3:   # optional PNG preview (needs a monospace TTF)
    import glob
    ttf=(glob.glob('/usr/share/fonts/**/DejaVuSansMono.ttf', recursive=True) or glob.glob('/home/*/.cache/**/DejaVuSansMono.ttf', recursive=True))[0]
    font=ImageFont.truetype(ttf, 14)
    cw=font.getlength('M'); lh=19; pad=16
    im=Image.new('RGB',(int(pad*2+TOTAL*cw), int(pad*2+len(lines)*lh)), C['bg']); d=ImageDraw.Draw(im)
    for idx,segs in enumerate(rows):
        x=pad
        for t,c in segs: d.text((x,pad+idx*lh), t, fill=c, font=font); x+=len(t)*cw
    im.save(sys.argv[3])
print(f'svg {W}x{H}, {len(lines)} lines, {TOTAL} cols')
