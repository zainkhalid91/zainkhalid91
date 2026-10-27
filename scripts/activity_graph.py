"""Draws my contribution activity for the last 31 days as light and dark SVGs.

Replaces github-readme-activity-graph.vercel.app, which stopped serving images.
Runs in the Snake workflow and publishes to the "output" branch next to the snake.

  GITHUB_TOKEN=... python scripts/activity_graph.py <user> <out_dir>
  python scripts/activity_graph.py <user> <out_dir> --input calendar.json   (offline, for testing)
"""
import json
import os
import sys
import urllib.request
from datetime import date

DAYS = 31
WIDTH, HEIGHT = 1000, 300
LEFT, RIGHT, TOP, BOTTOM = 56, 24, 56, 44

THEMES = {
    "activity-graph.svg": {"bg": "#ffffff", "text": "#57606a", "grid": "#d0d7de", "line": "#2da44e", "fill": "#2da44e", "dot": "#1a7f37"},
    "activity-graph-dark.svg": {"bg": "#0d1117", "text": "#8b949e", "grid": "#21262d", "line": "#3fb950", "fill": "#3fb950", "dot": "#56d364"},
}

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch(user):
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def last_days(payload):
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    return [(date.fromisoformat(d["date"]), d["contributionCount"]) for d in days[-DAYS:]]


def nice_max(value):
    # Round the axis up to 4, 8, 12... so the gridlines land on whole numbers.
    step = max(1, -(-value // 4))
    return step * 4


def svg(days, user, t):
    peak = nice_max(max(c for _, c in days) or 1)
    plot_w = WIDTH - LEFT - RIGHT
    plot_h = HEIGHT - TOP - BOTTOM
    def x(i): return LEFT + plot_w * i / (len(days) - 1)
    def y(c): return TOP + plot_h * (1 - c / peak)

    points = [(x(i), y(c)) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
    area = f"{LEFT:.1f},{TOP + plot_h:.1f} {line} {x(len(days) - 1):.1f},{TOP + plot_h:.1f}"
    total = sum(c for _, c in days)
    first, last = days[0][0], days[-1][0]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{user} made {total} contributions from {first:%d %b} to {last:%d %b %Y}">',
        f'<rect width="{WIDTH}" height="{HEIGHT}" rx="10" fill="{t["bg"]}"/>',
        f'<text x="{LEFT}" y="34" font-family="Segoe UI, Ubuntu, sans-serif" font-size="18" font-weight="600" fill="{t["text"]}">'
        f'Contributions, last {DAYS} days</text>',
        f'<text x="{WIDTH - RIGHT}" y="34" text-anchor="end" font-family="Segoe UI, Ubuntu, sans-serif" font-size="14" fill="{t["text"]}">'
        f'{total} in total</text>',
    ]
    for k in range(5):
        value = peak * k / 4
        gy = y(value)
        out.append(f'<line x1="{LEFT}" y1="{gy:.1f}" x2="{WIDTH - RIGHT}" y2="{gy:.1f}" stroke="{t["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{LEFT - 10}" y="{gy + 4:.1f}" text-anchor="end" font-family="Segoe UI, Ubuntu, sans-serif" '
                   f'font-size="12" fill="{t["text"]}">{int(value)}</text>')
    out.append(f'<polygon points="{area}" fill="{t["fill"]}" fill-opacity="0.18"/>')
    out.append(f'<polyline points="{line}" fill="none" stroke="{t["line"]}" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, ((day, count), (px, py)) in enumerate(zip(days, points)):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{t["dot"]}"><title>{day:%d %b}: {count}</title></circle>')
        if i % 5 == 0 or i == len(days) - 1:
            # Edge labels anchor inward so they aren't cut off.
            anchor = "start" if i == 0 else "end" if i == len(days) - 1 else "middle"
            out.append(f'<text x="{px:.1f}" y="{HEIGHT - 18}" text-anchor="{anchor}" font-family="Segoe UI, Ubuntu, sans-serif" '
                       f'font-size="12" fill="{t["text"]}">{day:%d %b}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    user, out_dir = sys.argv[1], sys.argv[2]
    if "--input" in sys.argv:
        with open(sys.argv[sys.argv.index("--input") + 1], encoding="utf-8") as f:
            payload = json.load(f)
    else:
        payload = fetch(user)
    days = last_days(payload)
    os.makedirs(out_dir, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
            f.write(svg(days, user, theme))
    print(f"Wrote {len(THEMES)} graphs for {len(days)} days to {out_dir}")


if __name__ == "__main__":
    main()
