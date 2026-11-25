"""Draws my GitHub year as a snowy pine bonsai, and decorates it as Christmas gets closer.

All winter: a lush pine bonsai under snow in a glazed pot, falling snow, warm fairy lights through
the branches, a stone lantern and a moonlit sky. From 1 December a string of coloured lights hangs
across the top and a small campfire burns beside the tree. From 14 December baubles, a star and a
couple of gifts appear. The numbers are this year's contributions, the current streak and the last
seven days, read from the contribution calendar. It runs nightly in the Profile graphics workflow
and publishes to the "output" branch.

  GITHUB_TOKEN=... python scripts/winter_tree.py <user> <out_dir>
  python scripts/winter_tree.py <user> <out_dir> --input calendar.json [--date 2026-12-20]
"""
import json
import math
import os
import random
import sys
import urllib.request
from datetime import date, timedelta

W, H = 830, 420
BASE = (232, 334)  # where the trunk leaves the soil; the tree sways around it

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch(user):
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def stats(payload):
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = sorted((date.fromisoformat(d["date"]), d["contributionCount"])
                  for w in cal["weeks"] for d in w["contributionDays"])
    today = days[-1][0]
    counts = dict(days)
    # A streak survives a quiet today: it counts back from yesterday when today is still empty.
    day = today if counts.get(today, 0) else today - timedelta(days=1)
    streak = 0
    while counts.get(day, 0) > 0:
        streak += 1
        day -= timedelta(days=1)
    week = sum(c for d, c in days if d > today - timedelta(days=7))
    return {"total": cal["totalContributions"], "streak": streak, "week": week, "today": today}


def stage(today):
    """How decorated the scene is: 0 plain winter, 1 lights and fire, 2 Christmas, 3 the days themselves."""
    if today.month != 12:
        return 0
    if 24 <= today.day <= 26:
        return 3
    if 14 <= today.day <= 26:
        return 2
    if today.day <= 26:
        return 1
    return 0


# ---------- geometry ----------

def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
            u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1])


def limb(points, w0, w1, steps=28):
    """A tapering limb along a chain of cubic segments, as one filled outline."""
    centre = []
    segs = [points[i:i + 4] for i in range(0, len(points) - 1, 3)]
    for si, seg in enumerate(segs):
        for k in range(steps + (1 if si == len(segs) - 1 else 0)):
            centre.append(bezier(*seg, k / steps))
    left, right = [], []
    n = len(centre)
    for i, (x, y) in enumerate(centre):
        a, b = centre[max(i - 1, 0)], centre[min(i + 1, n - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy) or 1
        nx, ny = -dy / length, dx / length
        half = (w0 + (w1 - w0) * (i / (n - 1))) / 2
        left.append((x + nx * half, y + ny * half))
        right.append((x - nx * half, y - ny * half))
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in left + right[::-1]) + "Z"


def sag(x0, y0, x1, y1, drop, t):
    """A point on a hanging string between two pins: a straight line with a parabolic sag."""
    return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + drop * 4 * t * (1 - t)


def pad(rng, cx, cy, w, h, fullness):
    """A pruned pine pad: a solid core, then needle clumps building a domed, lit top."""
    blobs = [(0, cx + dx * w * 0.3, cy + h * 0.08, h * 0.38) for dx in (-0.85, -0.3, 0.25, 0.8)]
    for _ in range(int(34 + 22 * fullness)):
        top = rng.random() < 0.72
        a = rng.uniform(math.pi, math.tau) if top else rng.uniform(0, math.pi)
        r = math.sqrt(rng.random())
        x = cx + math.cos(a) * r * w / 2 * 0.94
        y = cy + math.sin(a) * r * h / 2 * (1.0 if top else 0.35)
        rad = rng.uniform(0.17, 0.29) * h * (0.95 + 0.2 * fullness)
        # The moon is up and to the right, so clumps facing it are lighter.
        light = (x - cx) / w * 0.6 + (cy - y) / h * 1.2 + rng.uniform(-0.3, 0.3)
        tone = 0 if light < -0.2 else (1 if light < 0.25 else (2 if light < 0.6 else 3))
        blobs.append((tone, x, y, rad))
    blobs.sort(key=lambda b: (b[0], -b[3]))
    return blobs


def flame(scale):
    s = scale
    return (f"M0,0 C{-11*s:.1f},{-2*s:.1f} {-12*s:.1f},{-16*s:.1f} {-4*s:.1f},{-30*s:.1f} "
            f"C{-3*s:.1f},{-22*s:.1f} {2*s:.1f},{-20*s:.1f} {3*s:.1f},{-26*s:.1f} "
            f"C{9*s:.1f},{-18*s:.1f} {12*s:.1f},{-6*s:.1f} 0,0Z")


# ---------- styles ----------

CSS = """
svg{--sky1:#e4ecf5;--sky2:#f6f9fc;--hill1:#d3deea;--hill2:#e6edf5;--hill3:#f7fafd;--moon:#fff4d6;--moonglow:#ffe39a;
--pine0:#1f5236;--pine1:#2b6a45;--pine2:#3d8a58;--pine3:#5aa86f;--bark:#5a4636;--barkhi:#86684f;
--pot:#2b5d8c;--pothi:#4f86bb;--potlo:#1d4266;--snow:#ffffff;--flake:#8ea7c0;--star:#b5c4d6;
--text:#1f2328;--muted:#59636e;--line:#d0d7de;--accent:#2b5d8c;--stone:#8a8378;--stonedk:#6b655c;
--warm:#ffb53d;--log:#6b4a32;--logdk:#4a3222}
@media(prefers-color-scheme:dark){svg{--sky1:#050a16;--sky2:#101a2e;--hill1:#18223a;--hill2:#223050;--hill3:#304066;
--moon:#fff2c9;--moonglow:#ffdf8f;--pine0:#123a24;--pine1:#1b5233;--pine2:#287046;--pine3:#3c9160;--bark:#4a3a2f;
--barkhi:#72594a;--pot:#1d416a;--pothi:#3466a0;--potlo:#11294a;--snow:#eef4fa;--flake:#ffffff;--star:#e3ebf7;
--text:#e6edf3;--muted:#8b949e;--line:#30363d;--accent:#9cc3f0;--stone:#5c574f;--stonedk:#433f39;--warm:#ffbf4d;
--log:#5a3d29;--logdk:#3a271b}}
.flake{fill:var(--flake);animation:fa 12s linear infinite}
.fb{animation-name:fb}.fc{animation-name:fc}
.far{opacity:.45}.mid{opacity:.75}.near{opacity:.95;filter:url(#soft)}
@keyframes fa{from{transform:translate(0,0)}to{transform:translate(40px,450px)}}
@keyframes fb{from{transform:translate(0,0)}to{transform:translate(-30px,450px)}}
@keyframes fc{0%{transform:translate(0,0)}25%{transform:translate(14px,112px)}50%{transform:translate(-4px,225px)}75%{transform:translate(16px,338px)}100%{transform:translate(2px,450px)}}
.star{fill:var(--star);animation:tw 5s ease-in-out infinite}
@keyframes tw{0%,100%{opacity:.2}50%{opacity:1}}
.sway{transform-box:view-box;transform-origin:232px 334px;animation:sway 9s ease-in-out infinite}
@keyframes sway{0%,100%{transform:rotate(-1deg)}50%{transform:rotate(1deg)}}
.glow{animation:glow 6s ease-in-out infinite}
@keyframes glow{0%,100%{opacity:.6}50%{opacity:.9}}
.bulb{animation:blink 2.6s ease-in-out infinite}
@keyframes blink{0%,100%{opacity:.35}50%{opacity:1}}
.flicker{animation:flick 2.4s ease-in-out infinite}
@keyframes flick{0%,100%{opacity:.7}20%{opacity:1}45%{opacity:.8}70%{opacity:.95}}
.flame{transform-box:fill-box;transform-origin:50% 100%;animation:flame 1.1s ease-in-out infinite}
.flame.f2{animation-duration:.8s;animation-delay:-.3s}.flame.f3{animation-duration:.65s;animation-delay:-.5s}
@keyframes flame{0%,100%{transform:scale(1,1) skewX(0)}25%{transform:scale(.94,1.12) skewX(-5deg)}50%{transform:scale(1.04,.92) skewX(3deg)}75%{transform:scale(.97,1.08) skewX(-2deg)}}
.ember{fill:#ffc35a;opacity:0;animation:ember 2.8s ease-out infinite}
@keyframes ember{0%{opacity:0;transform:translate(0,0)}15%{opacity:1}100%{opacity:0;transform:translate(var(--dx),-95px)}}
.garland{transform-box:view-box;transform-origin:415px 0;animation:garl 7s ease-in-out infinite}
@keyframes garl{0%,100%{transform:rotate(.35deg)}50%{transform:rotate(-.35deg)}}
.bauble{transform-box:fill-box;transform-origin:50% 0;animation:swing 4s ease-in-out infinite}
@keyframes swing{0%,100%{transform:rotate(7deg)}50%{transform:rotate(-7deg)}}
.topstar{transform-box:fill-box;transform-origin:center;animation:pulse 3s ease-in-out infinite}
@keyframes pulse{0%,100%{transform:scale(1);opacity:.9}50%{transform:scale(1.08);opacity:1}}
.drop{fill:var(--snow);opacity:0;animation:drop 10s cubic-bezier(.5,0,.9,.6) infinite}
@keyframes drop{0%,64%{opacity:0;transform:translate(0,0)}66%{opacity:1;transform:translate(0,0)}92%{opacity:.9;transform:translate(6px,var(--fall))}100%{opacity:0;transform:translate(7px,var(--fall))}}
.num{font:600 44px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:var(--text);letter-spacing:-1px}
.big{font:600 22px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:var(--text)}
.label{font:400 13px -apple-system,"Segoe UI",system-ui,sans-serif;fill:var(--muted)}
.head{font:600 14px -apple-system,"Segoe UI",system-ui,sans-serif;fill:var(--text)}
.tag{font:500 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:var(--accent)}
@media(prefers-reduced-motion:reduce){*{animation:none!important}}
"""

BULB_COLOURS = ["#ff5a5f", "#ffc94a", "#4fd18b", "#5aa9ff", "#ff8ad8"]


def draw(s, user, today):
    rng = random.Random(1225)
    level = stage(today)
    fullness = min(1.0, s["total"] / 500)

    trunk = [BASE, (214, 300), (262, 276), (242, 244), (224, 214), (206, 186), (228, 158),
             (246, 132), (250, 116), (244, 96)]
    branches = [
        ([(238, 250), (210, 240), (180, 238), (150, 232)], 13, 4),
        ([(226, 212), (252, 198), (290, 190), (322, 176)], 12, 4),
        ([(232, 172), (210, 164), (190, 152), (164, 140)], 9, 3),
        ([(238, 280), (268, 282), (302, 278), (334, 262)], 11, 3.5),
        ([(240, 134), (262, 128), (282, 118), (296, 108)], 7, 2.5),
    ]
    pads = [(244, 84, 98, 42), (152, 228, 118, 42), (324, 170, 122, 44), (166, 140, 98, 36),
            (338, 258, 100, 36), (294, 106, 72, 30)]

    limbs = [limb(trunk, 28, 7)] + [limb(p, w0, w1) for p, w0, w1 in branches]
    foliage = []
    for cx, cy, w, h in pads:
        foliage += pad(rng, cx, cy, w, h, fullness)
    canopy = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>' for _, x, y, r in foliage)

    def tone(t):
        return "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>' for k, x, y, r in foliage if k == t)

    # Warm fairy lights looped across the front of every pad.
    fairy = []
    for i, (cx, cy, w, h) in enumerate(pads):
        x0, x1 = cx - w * 0.42, cx + w * 0.42
        y0 = cy - h * 0.05
        n = max(5, int(w / 14))
        pts = [sag(x0, y0, x1, y0 + 3, h * 0.32, k / (n - 1)) for k in range(n)]
        fairy.append('<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) +
                     '" fill="none" stroke="#3a2a1a" stroke-opacity=".35" stroke-width=".8"/>')
        for k, (x, y) in enumerate(pts):
            d = rng.uniform(0, 2.6)
            fairy.append(f'<circle class="bulb" cx="{x:.1f}" cy="{y:.1f}" r="1.9" fill="#ffd27a" '
                         f'style="animation-delay:-{d:.1f}s"/>')
    fairy = "".join(fairy)

    stars = "".join(
        f'<circle class="star" cx="{rng.uniform(20, 810):.0f}" cy="{rng.uniform(56, 250):.0f}" '
        f'r="{rng.choice([0.6, 0.8, 1.0, 1.3]):.1f}" style="animation-delay:-{rng.uniform(0, 5):.1f}s"/>'
        for _ in range(55))

    # Three depths of snow: small and slow far away, big, soft and quick up close.
    flakes = []
    for i in range(120):
        depth = rng.choices(["far", "mid", "near"], weights=[5, 4, 2])[0]
        size = {"far": rng.uniform(0.7, 1.2), "mid": rng.uniform(1.3, 2.0), "near": rng.uniform(2.3, 3.4)}[depth]
        dur = {"far": rng.uniform(16, 22), "mid": rng.uniform(10, 14), "near": rng.uniform(6.5, 9)}[depth]
        flakes.append(f'<circle class="flake f{"abc"[i % 3]} {depth}" cx="{rng.uniform(-30, W + 10):.0f}" cy="-10" '
                      f'r="{size:.1f}" style="animation-duration:{dur:.1f}s;animation-delay:-{rng.uniform(0, dur):.1f}s"/>')
    flakes = "".join(flakes)

    # Now and then a clump of snow slips off a pad's edge.
    drops = []
    for i, (cx, cy, w, h) in enumerate([pads[1], pads[2], pads[4], pads[3]]):
        side = -1 if cx < 232 else 1
        x, y = cx + side * w * 0.4, cy + h * 0.15
        land = 382 if abs(x - 232) > 85 else 330
        clump = "".join(f'<circle cx="{x + dx:.1f}" cy="{y + dy:.1f}" r="{r}"/>'
                        for dx, dy, r in ((0, 0, 3.2), (3.5, 1.5, 2.4), (-3, 2, 2.2), (1, -2.5, 2)))
        drops.append(f'<g class="drop" style="--fall:{land - y:.0f}px;animation-delay:-{i * 2.5}s">{clump}</g>')
    drops = "".join(drops)

    # ----- December -----
    garland = fire = ornaments = topstar = gifts = firelight = ""
    if level >= 1:
        pins = [(-10, 6), (210, 4), (420, 8), (630, 4), (840, 6)]
        wire, bulbs = [], []
        for (x0, y0), (x1, y1) in zip(pins, pins[1:]):
            pts = [sag(x0, y0, x1, y1, 22, k / 40) for k in range(41)]
            wire.append("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts))
            for k in range(2, 40, 5):
                x, y = sag(x0, y0, x1, y1, 22, k / 40)
                c = BULB_COLOURS[len(bulbs) % len(BULB_COLOURS)]
                d = (len(bulbs) * 0.37) % 2.6
                bulbs.append(
                    f'<g class="bulb" style="animation-delay:-{d:.2f}s">'
                    f'<circle cx="{x:.1f}" cy="{y + 6:.1f}" r="9" fill="{c}" opacity=".35" filter="url(#bloom)"/>'
                    f'<rect x="{x - 1.6:.1f}" y="{y:.1f}" width="3.2" height="3" rx="1" fill="#2b2b2b"/>'
                    f'<ellipse cx="{x:.1f}" cy="{y + 6.5:.1f}" rx="3" ry="4.2" fill="{c}"/></g>')
        garland = (f'<g class="garland"><path d="{" ".join(wire)}" fill="none" stroke="#1d2a22" stroke-width="1.4"/>'
                   f'{"".join(bulbs)}</g>')

        fx, fy = 420, 384
        embers = "".join(
            f'<circle class="ember" cx="{fx + rng.uniform(-6, 6):.1f}" cy="{fy - 30:.0f}" r="{rng.uniform(.9, 1.8):.1f}" '
            f'style="--dx:{rng.uniform(-18, 18):.0f}px;animation-delay:-{rng.uniform(0, 2.8):.1f}s;'
            f'animation-duration:{rng.uniform(2.2, 3.4):.1f}s"/>' for _ in range(16))
        stones = "".join(f'<ellipse cx="{fx + dx}" cy="{fy + 3 + abs(dx) * -0.05:.1f}" rx="8" ry="5" fill="var(--stone)"/>'
                         f'<ellipse cx="{fx + dx}" cy="{fy + 0.5 + abs(dx) * -0.05:.1f}" rx="6.5" ry="2" fill="var(--snow)"/>'
                         for dx in (-30, -17, 17, 30))
        firelight = (f'<ellipse cx="{fx}" cy="{fy - 4}" rx="150" ry="70" fill="url(#firelight)" class="flicker"/>'
                     f'<ellipse cx="{fx}" cy="{fy + 2}" rx="64" ry="13" fill="#ffb14a" opacity=".32" class="flicker"/>')
        fire = (f'<g>{stones}'
                f'<rect x="{fx - 25}" y="{fy - 7}" width="50" height="9" rx="4.5" fill="var(--log)" transform="rotate(-14 {fx} {fy})"/>'
                f'<rect x="{fx - 25}" y="{fy - 7}" width="50" height="9" rx="4.5" fill="var(--logdk)" transform="rotate(14 {fx} {fy})"/>'
                f'<g transform="translate({fx} {fy - 4})">'
                f'<path class="flame" d="{flame(1.75)}" fill="#ff6a1a"/>'
                f'<path class="flame f2" d="{flame(1.25)}" fill="#ffa726" transform="translate(-2 0)"/>'
                f'<path class="flame f3" d="{flame(0.78)}" fill="#fff0a6" transform="translate(-1 0)"/></g>'
                f'{embers}</g>')

    if level >= 2:
        orn = []
        hooks = [(118, 244), (150, 250), (188, 246), (290, 190), (330, 194), (362, 186), (140, 156),
                 (190, 154), (310, 274), (352, 276), (226, 104), (266, 104)]
        for i, (x, y) in enumerate(hooks):
            c = ["#e23b4a", "#f2b632", "#3e8ee0", "#e23b4a", "#c9cfd8", "#f2b632"][i % 6]
            L = 6 + (i % 3) * 2
            orn.append(f'<g class="bauble" style="animation-delay:-{i * 0.45:.2f}s;animation-duration:{3.5 + (i % 4) * 0.4:.1f}s">'
                       f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + L}" stroke="#d9c38a" stroke-width=".7"/>'
                       f'<circle cx="{x}" cy="{y + L + 3.6}" r="3.8" fill="{c}"/>'
                       f'<circle cx="{x - 1.2}" cy="{y + L + 2.4}" r="1.1" fill="#fff" opacity=".7"/></g>')
        ornaments = "".join(orn)
        sx, sy, R = 244, 50, 11
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            r = R if k % 2 == 0 else R * 0.45
            pts.append(f"{sx + math.cos(a) * r:.1f},{sy + math.sin(a) * r:.1f}")
        topstar = (f'<circle cx="{sx}" cy="{sy}" r="22" fill="url(#starglow)" class="glow"/>'
                   f'<polygon class="topstar" points="{" ".join(pts)}" fill="#ffd34d" stroke="#f2a71b" stroke-width=".8"/>')
        gifts = (
            '<g transform="translate(300 352)">'
            '<rect x="0" y="6" width="22" height="18" rx="1.5" fill="#c62f3c"/><rect x="9" y="6" width="4" height="18" fill="#f3d27a"/>'
            '<rect x="-1" y="3" width="24" height="5" rx="1.5" fill="#a92633"/><path d="M11,3 C6,-4 2,1 11,3 C20,1 16,-4 11,3Z" fill="#f3d27a"/>'
            '<path d="M-1,4 C6,0 16,0 23,4 C20,5 3,5 -1,4Z" fill="var(--snow)"/>'
            '<rect x="26" y="12" width="16" height="12" rx="1.5" fill="#2d7a4f"/><rect x="32" y="12" width="3.5" height="12" fill="#f3d27a"/>'
            '<path d="M25,12.5 C31,9.5 37,9.5 43,12.5 C38,13.5 30,13.5 25,12.5Z" fill="var(--snow)"/></g>')

    total, streak, week = s["total"], s["streak"], s["week"]
    tag = "merry christmas" if level == 3 else "winter"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" lang="en">
<title>A pine bonsai in the snow: {total} contributions this year, a {streak} day streak, {week} in the last 7 days.</title>
<desc>A snow covered pine bonsai in a glazed pot on a winter night, with warm fairy lights, falling snow and a stone lantern{', a string of coloured lights and a campfire' if level >= 1 else ''}{', baubles, a star and gifts' if level >= 2 else ''}. Drawn from the GitHub history of {user} on {today.isoformat()}.</desc>
<style>{CSS}</style>
<defs>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--sky1)"/><stop offset="1" stop-color="var(--sky2)"/></linearGradient>
<radialGradient id="moonglow"><stop offset="0" stop-color="var(--moonglow)" stop-opacity=".45"/><stop offset="1" stop-color="var(--moonglow)" stop-opacity="0"/></radialGradient>
<radialGradient id="lampglow"><stop offset="0" stop-color="var(--warm)" stop-opacity=".6"/><stop offset="1" stop-color="var(--warm)" stop-opacity="0"/></radialGradient>
<radialGradient id="firelight"><stop offset="0" stop-color="#ff9a3c" stop-opacity=".38"/><stop offset=".5" stop-color="#ff7a2a" stop-opacity=".12"/><stop offset="1" stop-color="#ff7a2a" stop-opacity="0"/></radialGradient>
<radialGradient id="starglow"><stop offset="0" stop-color="#ffd34d" stop-opacity=".6"/><stop offset="1" stop-color="#ffd34d" stop-opacity="0"/></radialGradient>
<radialGradient id="treeglow"><stop offset="0" stop-color="#ffcf7a" stop-opacity=".16"/><stop offset="1" stop-color="#ffcf7a" stop-opacity="0"/></radialGradient>
<linearGradient id="pot" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="var(--potlo)"/><stop offset=".38" stop-color="var(--pothi)"/><stop offset="1" stop-color="var(--potlo)"/></linearGradient>
<filter id="soft" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation=".7"/></filter>
<filter id="bloom" x="-1" y="-1" width="3" height="3"><feGaussianBlur stdDeviation="3"/></filter>
<filter id="fairyglow" x="-.2" y="-.2" width="1.4" height="1.4"><feGaussianBlur stdDeviation="2.2"/></filter>
<mask id="crescent" maskUnits="userSpaceOnUse" x="420" y="60" width="70" height="70"><circle cx="452" cy="92" r="19" fill="#fff"/><circle cx="461" cy="85" r="16" fill="#000"/></mask>
<clipPath id="card"><rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12"/></clipPath>
<g id="canopy">{canopy}</g>
<mask id="caps" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><use href="#canopy" fill="#fff"/><use href="#canopy" fill="#000" transform="translate(1.5 9)"/></mask>
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="url(#sky)"/>
{stars}
<circle cx="452" cy="92" r="72" fill="url(#moonglow)" class="glow"/>
<circle cx="452" cy="92" r="19" fill="var(--moon)" mask="url(#crescent)"/>
<path d="M0,334 C90,310 170,320 260,328 C360,336 430,298 540,306 C640,313 720,294 830,304 V420 H0Z" fill="var(--hill1)"/>
<path d="M0,360 C120,344 200,354 300,356 C420,358 520,338 640,344 C720,348 780,340 830,342 V420 H0Z" fill="var(--hill2)"/>
<ellipse cx="240" cy="190" rx="170" ry="150" fill="url(#treeglow)" class="glow"/>
{firelight}
<g transform="translate(70 312)">
  <ellipse cx="0" cy="8" rx="40" ry="30" fill="url(#lampglow)" class="flicker"/>
  <rect x="-3" y="18" width="6" height="22" fill="var(--stonedk)"/>
  <rect x="-11" y="38" width="22" height="5" rx="1.5" fill="var(--stonedk)"/>
  <rect x="-9" y="2" width="18" height="15" rx="2" fill="var(--stone)"/>
  <rect x="-5" y="5" width="10" height="9" rx="1" fill="#ffcf6b" class="flicker"/>
  <path d="M-15,3 L0,-9 L15,3Z" fill="var(--stone)"/>
  <path d="M-16,2 C-10,-4 -4,-9 0,-11 C4,-9 10,-4 16,2 C10,0 -10,0 -16,2Z" fill="var(--snow)"/>
  <rect x="-1.5" y="-15" width="3" height="5" rx="1" fill="var(--stone)"/>
</g>
<g class="sway">
  <g fill="var(--bark)">{"".join(f'<path d="{d}"/>' for d in limbs)}</g>
  <path d="{limb(trunk, 8, 2)}" fill="var(--barkhi)" opacity=".5" transform="translate(4 -1)"/>
  <g fill="var(--pine0)">{tone(0)}</g>
  <g fill="var(--pine1)">{tone(1)}</g>
  <g fill="var(--pine2)">{tone(2)}</g>
  <g fill="var(--pine3)">{tone(3)}</g>
  <rect width="{W}" height="{H}" fill="var(--snow)" mask="url(#caps)"/>
  <g filter="url(#fairyglow)" opacity=".8">{fairy}</g>
  {fairy}
  {ornaments}
  {topstar}
</g>
<ellipse cx="232" cy="378" rx="128" ry="12" fill="var(--hill1)" opacity=".7"/>
<path d="M158,334 H306 L294,370 H170Z" fill="url(#pot)"/>
<rect x="150" y="328" width="164" height="10" rx="3" fill="var(--pothi)"/>
<rect x="174" y="368" width="16" height="8" rx="2" fill="var(--potlo)"/>
<rect x="274" y="368" width="16" height="8" rx="2" fill="var(--potlo)"/>
<path d="M150,330 C170,318 200,316 232,320 C266,316 296,318 314,330 C312,335 306,334 302,337 C300,342 296,342 294,337 C270,333 200,333 172,337 C170,344 165,345 163,338 C158,337 152,337 150,330Z" fill="var(--snow)"/>
{gifts}
<path d="M0,386 C80,374 160,384 232,386 C330,388 420,374 520,378 C640,382 740,372 830,376 V420 H0Z" fill="var(--hill3)"/>
{fire}
{drops}
{flakes}
{garland}
<text class="head" x="28" y="{58 if level >= 1 else 40}">@{user}</text>
<text class="tag" x="{W - 28}" y="{58 if level >= 1 else 40}" text-anchor="end">{tag} · {today.isoformat()}</text>
<g transform="translate(560 118)">
  <text class="num" x="0" y="0">{total}</text>
  <text class="label" x="2" y="22">contributions this year</text>
  <text class="big" x="0" y="66">{streak} day streak</text>
  <text class="big" x="0" y="98">{week} this week</text>
  <text class="label" x="2" y="140">Redrawn every night from my GitHub.</text>
</g>
</g>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="var(--line)"/>
</svg>
"""


def main():
    user, out_dir = sys.argv[1], sys.argv[2]
    if "--input" in sys.argv:
        with open(sys.argv[sys.argv.index("--input") + 1], encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = fetch(user)
    s = stats(payload)
    today = date.fromisoformat(sys.argv[sys.argv.index("--date") + 1]) if "--date" in sys.argv else s["today"]
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "winter-tree.svg"), "w", encoding="utf-8", newline="\n") as f:
        f.write(draw(s, user, today))


if __name__ == "__main__":
    main()
