"""Generate assets/contributions.svg: weekly GitHub contributions over the last year."""
import datetime as dt
import json
import os
import urllib.request

USER = os.environ.get("GH_USER", "feranando0241")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = "assets/contributions.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = []
    for w in cal["weeks"]:
        days = w["contributionDays"]
        weeks.append((days[0]["date"], sum(d["contributionCount"] for d in days)))
    return cal["totalContributions"], weeks


def render(total, weeks):
    W, H = 900, 260
    left, right, top, bottom = 50, 20, 60, 40
    pw, ph = W - left - right, H - top - bottom
    peak = max((c for _, c in weeks), default=0) or 1
    n = len(weeks)
    step = pw / max(n - 1, 1)

    pts = [(left + i * step, top + ph - (c / peak) * ph) for i, (_, c) in enumerate(weeks)]

    # smooth path (Catmull-Rom -> Bezier)
    def smooth(p):
        d = f"M{p[0][0]:.1f},{p[0][1]:.1f}"
        for i in range(len(p) - 1):
            p0 = p[i - 1] if i else p[i]
            p1, p2 = p[i], p[i + 1]
            p3 = p[i + 2] if i + 2 < len(p) else p2
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            c1 = (c1[0], max(top, min(c1[1], top + ph)))
            c2 = (c2[0], max(top, min(c2[1], top + ph)))
            d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
        return d

    line = smooth(pts)
    area = f"{line} L{pts[-1][0]:.1f},{top + ph} L{pts[0][0]:.1f},{top + ph} Z"

    grid = ""
    for k in range(5):
        y = top + ph * k / 4
        val = round(peak * (1 - k / 4))
        grid += f'<line x1="{left}" y1="{y:.1f}" x2="{W - right}" y2="{y:.1f}" class="grid"/>'
        grid += f'<text x="{left - 10}" y="{y + 4:.1f}" class="axis" text-anchor="end">{val}</text>'

    months, last = "", None
    for i, (date, _) in enumerate(weeks):
        d = dt.date.fromisoformat(date)
        if d.month != last and d.day <= 7:
            months += f'<text x="{left + i * step:.1f}" y="{H - 12}" class="axis" text-anchor="middle">{d.strftime("%b")}</text>'
            last = d.month

    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="dot"/>' for (x, y), (_, c) in zip(pts, weeks) if c
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
  text {{ font-family: Nunito, "Varela Round", "Segoe UI", -apple-system, sans-serif; }}
  .title {{ fill: #38BDF8; font-size: 20px; font-weight: 800; }}
  .sub {{ fill: #7DD3FC; font-size: 13px; }}
  .axis {{ fill: #7DD3FC; font-size: 11px; opacity: .85; }}
  .grid {{ stroke: #38BDF8; stroke-opacity: .15; stroke-dasharray: 4 4; }}
  .line {{ fill: none; stroke: #38BDF8; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }}
  .dot {{ fill: #E0F2FE; stroke: #0EA5E9; stroke-width: 1.5; }}
</style>
<defs>
  <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#38BDF8" stop-opacity=".45"/>
    <stop offset="1" stop-color="#38BDF8" stop-opacity="0"/>
  </linearGradient>
</defs>
<text x="{left}" y="28" class="title">Contributions</text>
<text x="{left}" y="47" class="sub">{total} in the last year · updated {dt.date.today():%b %d, %Y}</text>
{grid}
<path d="{area}" fill="url(#fill)"/>
<path d="{line}" class="line"/>
{dots}
{months}
</svg>
'''


if __name__ == "__main__":
    total, weeks = fetch()
    os.makedirs("assets", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(render(total, weeks))
    print(f"wrote {OUT}: {total} contributions, {len(weeks)} weeks")
