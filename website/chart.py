"""The rating history chart, drawn as inline SVG with coloured tier bands."""

from datetime import date
from html import escape

from .theme import TIERS, tier

WIDTH, HEIGHT = 820, 300
LEFT, RIGHT, TOP, BOTTOM = 52, 18, 16, 34


def rating_chart(points: list[dict]) -> str:
    """`points`: dicts with date, rating, contest, rank, teams, oldest first."""
    ratings = [p["rating"] for p in points]
    # Fit the data with some room, on round hundreds, spanning at least 800 points.
    low = max(0, (min(ratings) - 200) // 200 * 200)
    high = -(-(max(ratings) + 200) // 200) * 200
    if high - low < 800:
        low = max(0, low - (800 - (high - low)) // 2 // 200 * 200)
        high = low + 800

    days = [(p["date"] - points[0]["date"]).days for p in points]
    span = max(days[-1], 1)
    plot_w, plot_h = WIDTH - LEFT - RIGHT, HEIGHT - TOP - BOTTOM

    def x(i: int) -> float:
        return LEFT + (plot_w / 2 if len(points) == 1 else plot_w * days[i] / span)

    def y(value: float) -> float:
        return TOP + plot_h * (1 - (value - low) / (high - low))

    parts = [f'<svg class="chart" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="Rating history">']
    # Tier bands and their boundary labels; a label too close to the one below it is skipped.
    last_label = None
    for i, bottom in enumerate(TIERS):
        top = TIERS[i + 1] if i + 1 < len(TIERS) else 10 ** 6
        band_low, band_high = max(bottom, low), min(top, high)
        if band_low >= band_high:
            continue
        parts.append(
            f'<rect class="band tier-{i}" x="{LEFT}" y="{y(band_high):.1f}" '
            f'width="{plot_w}" height="{y(band_low) - y(band_high):.1f}"/>'
        )
        if bottom > low and (last_label is None or last_label - y(bottom) >= 14):
            parts.append(f'<text class="axis" x="{LEFT - 8}" y="{y(bottom) + 4:.1f}" text-anchor="end">{bottom}</text>')
            last_label = y(bottom)
    parts.append(f'<rect class="frame" x="{LEFT}" y="{TOP}" width="{plot_w}" height="{plot_h}"/>')

    # Year labels along the bottom.
    first, last = points[0]["date"], points[-1]["date"]
    for year in range(first.year + 1, last.year + 1):
        offset = (date(year, 1, 1) - first).days
        if 0 < offset < span:
            px = LEFT + plot_w * offset / span
            parts.append(f'<line class="year" x1="{px:.1f}" y1="{TOP}" x2="{px:.1f}" y2="{TOP + plot_h}"/>')
            parts.append(f'<text class="axis" x="{px:.1f}" y="{HEIGHT - 12}" text-anchor="middle">{year}</text>')

    path = " ".join(f"{'M' if i == 0 else 'L'}{x(i):.1f},{y(p['rating']):.1f}" for i, p in enumerate(points))
    parts.append(f'<path class="line" d="{path}"/>')
    for i, p in enumerate(points):
        label = (
            f"{p['contest']} · {p['date']:%d %b %Y}|Rating {p['rating']}"
            + (f" · Rank {p['rank']} of {p['teams']}" if p["rank"] is not None else "")
        )
        parts.append(
            f'<circle class="point tier-{tier(p["rating"])}" cx="{x(i):.1f}" cy="{y(p["rating"]):.1f}" r="5" '
            f'tabindex="0" data-tip="{escape(label)}"><title>{escape(label.replace("|", " · "))}</title></circle>'
        )
    parts.append("</svg>")
    return "".join(parts)
