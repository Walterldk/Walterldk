import base64
import io
import json
import math
import os
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "contributions.json"
STATIC = os.environ.get("STATIC") == "1"
OUT_DIR = ROOT / "assets" / ("static" if STATIC else "")

C = {
    "bg": "#0a1020",
    "panel": "#0f1b33",
    "line": "#1e3a5f",
    "blue": "#3b82f6",
    "cyan": "#22d3ee",
    "text": "#e6edf3",
    "muted": "#8b9bb4",
    "ok": "#34d399",
}
HEAT = ["#14233f", "#1e3a8a", "#2563eb", "#38bdf8", "#a5f3fc"]
MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
WEEKDAYS = ["", "Lun", "", "Mié", "", "Vie", ""]
FONT = "'WS Mono', ui-monospace, Menlo, Consolas, monospace"
GLYPHS = list(range(0x20, 0x7F)) + [ord(c) for c in "áéíóúüñÁÉÍÓÚÜÑ¿¡·—•→"]

ANIM_CSS = """
.fade{opacity:0;animation:fade .8s ease forwards}
@keyframes fade{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.eq{transform-box:fill-box;transform-origin:bottom;animation:eq 1.1s ease-in-out infinite}
@keyframes eq{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}
"""


@cache
def embedded_fonts():
    from fontTools.subset import Options, Subsetter
    from fontTools.ttLib import TTFont
    from matplotlib import get_data_path

    base = Path(get_data_path()) / "fonts" / "ttf"
    faces = []
    for file, weight in (("DejaVuSansMono.ttf", 400), ("DejaVuSansMono-Bold.ttf", 700)):
        font = TTFont(str(base / file), recalcTimestamp=False)
        options = Options()
        options.drop_tables += ["FFTM"]
        subsetter = Subsetter(options)
        subsetter.populate(unicodes=GLYPHS)
        subsetter.subset(font)
        font.flavor = "woff"
        buffer = io.BytesIO()
        font.save(buffer)
        encoded = base64.b64encode(buffer.getvalue()).decode()
        faces.append(
            f"@font-face{{font-family:'WS Mono';font-weight:{weight};"
            f"src:url(data:font/woff;base64,{encoded}) format('woff')}}"
        )
    return "".join(faces)


def fade(delay):
    return "" if STATIC else f'class="fade" style="animation-delay:{delay:.2f}s"'


def animate(attr, start, end, dur, begin=0):
    if STATIC:
        return ""
    return (
        f'<animate attributeName="{attr}" from="{start}" to="{end}" '
        f'dur="{dur}s" begin="{begin:.2f}s" fill="freeze"/>'
    )


def loop(attr, values, dur, begin=0, discrete=False):
    if STATIC:
        return ""
    mode = ' calcMode="discrete"' if discrete else ""
    return (
        f'<animate attributeName="{attr}" values="{values}" dur="{dur}s" '
        f'begin="{begin}s" repeatCount="indefinite"{mode}/>'
    )


def spin(cx, cy, dur, reverse=False):
    if STATIC:
        return ""
    start, end = (360, 0) if reverse else (0, 360)
    return (
        f'<animateTransform attributeName="transform" type="rotate" '
        f'from="{start} {cx} {cy}" to="{end} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/>'
    )


def svg(width, height, body, label):
    css = embedded_fonts() + f"text{{font-family:{FONT}}}" + ("" if STATIC else ANIM_CSS)
    label = escape(label, {'"': "&quot;"})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">'
        f"<style>{css}</style>{body}</svg>"
    )


def text(x, y, content, size, fill, weight=400, anchor="start", extra=""):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}" {extra}>{escape(content)}</text>'
    )


def text_width(content, size):
    return len(content) * size * 0.602


def load_days(data):
    days = sorted((date.fromisoformat(d["date"]), d["count"]) for d in data.get("days", []))
    if not days:
        today = date.today()
        days = [(today - timedelta(days=364 - i), 0) for i in range(365)]
    return days


def current_streak(days):
    counts = [count for _, count in days]
    if counts and counts[-1] == 0:
        counts = counts[:-1]
    streak = 0
    for count in reversed(counts):
        if count == 0:
            break
        streak += 1
    return streak


def monthly_totals(days):
    last = days[-1][0]
    keys = []
    year, month = last.year, last.month
    for _ in range(12):
        keys.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    keys.reverse()
    totals = {key: 0 for key in keys}
    for day, count in days:
        key = (day.year, day.month)
        if key in totals:
            totals[key] += count
    return [(MONTHS[month - 1], totals[(year, month)]) for year, month in keys]


def hero(profile):
    width, height = 1200, 320
    handle = profile["handle"]
    prompt = f"~/{handle.lower()} $ whoami"
    cursor_x = 60 + text_width(prompt, 18) + 6

    chips = ""
    x = 60
    for i, skill in enumerate(profile["skills"]):
        chip_width = int(text_width(skill["name"], 16) + 36)
        chips += (
            f'<g {fade(1.6 + i * 0.2)}>'
            f'<rect x="{x}" y="268" width="{chip_width}" height="34" rx="17" fill="{C["panel"]}" stroke="{C["blue"]}"/>'
            f'{text(x + chip_width / 2, 290, skill["name"], 16, C["cyan"], anchor="middle")}</g>'
        )
        x += chip_width + 12

    reveal_attr = "" if STATIC else ' clip-path="url(#reveal)"'
    reveal_def = (
        ""
        if STATIC
        else f'<clipPath id="reveal"><rect x="40" y="90" width="0" height="120">'
        f'{animate("width", 0, 1000, 1.6, 0.3)}</rect></clipPath>'
    )

    body = f"""
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C['bg']}"/><stop offset="1" stop-color="#10264d"/></linearGradient>
<linearGradient id="tg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#60a5fa"/><stop offset="1" stop-color="{C['cyan']}"/></linearGradient>
<radialGradient id="glow"><stop offset="0" stop-color="{C['blue']}" stop-opacity=".38"/><stop offset="1" stop-color="{C['blue']}" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{C['line']}" stroke-opacity=".35"/></pattern>
<clipPath id="frame"><rect width="{width}" height="{height}" rx="20"/></clipPath>
{reveal_def}
</defs>
<g clip-path="url(#frame)">
<rect width="{width}" height="{height}" fill="url(#bg)"/>
<rect width="{width}" height="{height}" fill="url(#grid)"/>
<circle cx="220" cy="40" r="200" fill="url(#glow)">{loop("cx", "220;340;220", 14)}</circle>
<circle cx="1000" cy="300" r="220" fill="url(#glow)">{loop("cx", "1000;900;1000", 16)}</circle>
</g>
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="20" fill="none" stroke="{C['line']}" stroke-width="2"/>
{text(60, 78, prompt, 18, C['muted'])}
<rect x="{cursor_x:.1f}" y="62" width="10" height="20" fill="{C['cyan']}">{loop("opacity", "1;0;1", 1, discrete=True)}</rect>
<g{reveal_attr}>{text(58, 170, profile['name'], 76, "url(#tg)", 700)}</g>
<g {fade(1.0)}>
{text(60, 216, profile['role'] + " · " + profile['school'], 22, C['text'])}
{text(60, 248, profile['focus'], 18, C['cyan'])}
</g>
{chips}
<g>
<circle cx="1030" cy="160" r="96" fill="none" stroke="{C['blue']}" stroke-width="2" stroke-dasharray="6 14">{spin(1030, 160, 30)}</circle>
<circle cx="1030" cy="160" r="66" fill="none" stroke="{C['cyan']}" stroke-width="2" stroke-dasharray="40 18">{spin(1030, 160, 18, True)}</circle>
<circle cx="1030" cy="160" r="38" fill="{C['panel']}" stroke="{C['blue']}" stroke-width="2"/>
{text(1030, 172, "</>", 32, C['cyan'], 700, "middle")}
</g>
"""
    return svg(width, height, body, f"{profile['name']}, {profile['role']}")


def tile(num, title, subtitle, content, label):
    width, height = 420, 300
    body = f"""
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="18" fill="{C['panel']}" stroke="{C['line']}" stroke-width="2"/>
<rect x="28" y="30" width="46" height="4" rx="2" fill="{C['cyan']}">{animate("width", 0, 46, 0.8)}</rect>
{text(28, 62, num + " / " + title, 14, C['muted'])}
{text(28, 104, title, 40, C['text'], 700)}
{text(28, 130, subtitle, 17, C['cyan'])}
{content}
"""
    return svg(width, height, body, label)


def build(profile):
    rows = ""
    for i, skill in enumerate(profile["skills"][:3]):
        y = 168 + i * 42
        fill_width = 364 * skill["level"] / 100
        delay = 0.4 + i * 0.25
        rows += f"""
<g {fade(delay)}>{text(28, y, skill['name'], 17, C['text'], 700)}{text(392, y, str(skill['level']) + "%", 15, C['muted'], anchor="end")}</g>
<rect x="28" y="{y + 10}" width="364" height="10" rx="5" fill="{C['bg']}"/>
<rect x="28" y="{y + 10}" width="{0 if not STATIC else fill_width:.1f}" height="10" rx="5" fill="{C['blue']}">{animate("width", 0, f"{fill_width:.1f}", 1.1, delay)}</rect>
"""
    return tile("01", "BUILD", profile["focus"], rows, "BUILD: habilidades backend")


def brand(profile):
    initials = "".join(part[0] for part in profile["name"].split()[:2]).upper()
    chips = ""
    x = 28
    for i, interest in enumerate(profile["interests"]):
        chip_width = int(text_width(interest, 15) + 26)
        chips += (
            f'<g {fade(1.0 + i * 0.2)}>'
            f'<rect x="{x}" y="226" width="{chip_width}" height="32" rx="16" fill="{C["bg"]}" stroke="{C["line"]}"/>'
            f'{text(x + chip_width / 2, 247, interest, 15, C["text"], anchor="middle")}</g>'
        )
        x += chip_width + 10

    bars = ""
    for i in range(6):
        height = 10 + (i * 7) % 22
        delay = f"animation-delay:-{i * 0.17:.2f}s"
        bars += (
            f'<rect class="eq" x="{336 + i * 10}" y="{62 - height}" width="6" height="{height}" '
            f'rx="2" fill="{C["cyan"]}" style="{delay}"/>'
            if not STATIC
            else f'<rect x="{336 + i * 10}" y="{62 - height}" width="6" height="{height}" rx="2" fill="{C["cyan"]}"/>'
        )

    content = f"""
{bars}
<circle cx="76" cy="184" r="34" fill="none" stroke="{C['cyan']}" stroke-width="2">
{loop("r", "34;50;34", 2.4)}{loop("opacity", "0.9;0;0.9", 2.4)}</circle>
<circle cx="76" cy="184" r="34" fill="{C['bg']}" stroke="{C['blue']}" stroke-width="2"/>
{text(76, 194, initials, 26, C['cyan'], 700, "middle")}
<g {fade(0.5)}>
{text(130, 178, profile['name'], 20, C['text'], 700)}
{text(130, 202, "@" + profile['handle'], 15, C['muted'])}
</g>
{chips}
"""
    return tile("02", "BRAND", profile["school"] + " · ADSO", content, "BRAND: identidad e intereses")


def learn(profile):
    items = profile["roadmap"][:4]
    labels = {"done": "listo", "doing": "en curso", "next": "próximo"}
    top = 170
    step = 36
    nodes = ""
    for i, item in enumerate(items):
        y = top + i * step
        status = item["status"]
        delay = 0.4 + i * 0.3
        if status == "done":
            mark = (
                f'<circle cx="38" cy="{y}" r="9" fill="{C["ok"]}"/>'
                f'<path d="M33 {y}l4 4l7 -8" fill="none" stroke="{C["bg"]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            )
            color = C["text"]
        elif status == "doing":
            mark = (
                f'<circle cx="38" cy="{y}" r="9" fill="{C["cyan"]}"/>'
                f'<circle cx="38" cy="{y}" r="9" fill="none" stroke="{C["cyan"]}" stroke-width="2">'
                f'{loop("r", "9;18;9", 1.8)}{loop("opacity", "0.9;0;0.9", 1.8)}</circle>'
            )
            color = C["cyan"]
        else:
            mark = f'<circle cx="38" cy="{y}" r="8" fill="none" stroke="{C["muted"]}" stroke-width="2"/>'
            color = C["muted"]
        nodes += (
            f'<g {fade(delay)}>{mark}{text(62, y + 6, item["name"], 16, color, 700 if status == "doing" else 400)}'
            f'{text(392, y + 5, labels[status], 12, C["muted"], anchor="end")}</g>'
        )
    line_end = top + (len(items) - 1) * step
    content = (
        f'<line x1="38" y1="{top}" x2="38" y2="{line_end}" stroke="{C["line"]}" stroke-width="2"/>'
        f"{nodes}"
    )
    return tile("03", "LEARN", "Formación en el SENA", content, "LEARN: ruta de aprendizaje")


def activity(days):
    width, height = 1200, 300
    months = monthly_totals(days)
    total = sum(value for _, value in months)
    base, max_height = 246, 140
    peak = max(max(value for _, value in months), 1)
    step = 90
    left = 60

    grid = ""
    for i in range(4):
        y = base - i * max_height / 3
        grid += f'<line x1="{left - 10}" y1="{y:.1f}" x2="{width - 40}" y2="{y:.1f}" stroke="{C["line"]}" stroke-opacity=".5" stroke-dasharray="4 8"/>'

    bars = ""
    for i, (month, value) in enumerate(months):
        bar_height = max(value / peak * max_height, 4 if value else 0)
        x = left + i * step + 10
        delay = 0.2 + i * 0.08
        fill = C["cyan"] if value == peak and value > 0 else C["blue"]
        if STATIC:
            rect = f'<rect x="{x}" y="{base - bar_height:.1f}" width="56" height="{bar_height:.1f}" rx="6" fill="{fill}"/>'
        else:
            rect = (
                f'<rect x="{x}" y="{base}" width="56" height="0" rx="6" fill="{fill}">'
                f'{animate("height", 0, f"{bar_height:.1f}", 0.9, delay)}'
                f'{animate("y", base, f"{base - bar_height:.1f}", 0.9, delay)}</rect>'
            )
        bars += rect
        bars += f'<g {fade(delay + 0.7)}>{text(x + 28, base - bar_height - 10, str(value), 15, C["text"], 700, "middle")}</g>'
        bars += text(x + 28, base + 28, month, 15, C["muted"], anchor="middle")

    body = f"""
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="20" fill="{C['panel']}" stroke="{C['line']}" stroke-width="2"/>
{text(40, 54, "Actividad mensual", 26, C['text'], 700)}
{text(width - 40, 54, f"Últimos 12 meses · {total} contribuciones", 16, C['muted'], anchor="end")}
{grid}
{bars}
"""
    return svg(width, height, body, f"Actividad mensual: {total} contribuciones en 12 meses")


def graph(days):
    width, height = 1200, 300
    left, top, size, gap = 56, 96, 17, 4
    pitch = size + gap
    peak = max(count for _, count in days)
    total = sum(count for _, count in days)
    streak = current_streak(days)
    offset = (days[0][0].weekday() + 1) % 7

    cells = ""
    labels = ""
    last_month = None
    last_label_col = -10
    for n, (day, count) in enumerate(days):
        index = offset + n
        col, row = divmod(index, 7)
        x, y = left + col * pitch, top + row * pitch
        level = 0 if count == 0 else min(4, max(1, math.ceil(4 * count / peak)))
        delay = col * 0.025 + row * 0.01
        if STATIC:
            cells += f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{HEAT[level]}"/>'
        else:
            cells += (
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="{HEAT[level]}" opacity="0">'
                f'{animate("opacity", 0, 1, 0.35, delay)}</rect>'
            )
        if day.month != last_month and col - last_label_col >= 3:
            labels += text(x, top - 14, MONTHS[day.month - 1], 14, C["muted"])
            last_label_col = col
        last_month = day.month

    weekday_labels = "".join(
        text(left - 12, top + i * pitch + 13, name, 12, C["muted"], anchor="end")
        for i, name in enumerate(WEEKDAYS)
        if name
    )
    legend_x = width - 40 - 5 * pitch - 90
    legend = (
        text(legend_x, height - 26, "Menos", 13, C["muted"], anchor="end")
        + "".join(
            f'<rect x="{legend_x + 10 + i * pitch}" y="{height - 38}" width="{size}" height="{size}" rx="3" fill="{HEAT[i]}"/>'
            for i in range(5)
        )
        + text(legend_x + 18 + 5 * pitch, height - 26, "Más", 13, C["muted"])
    )

    body = f"""
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="20" fill="{C['panel']}" stroke="{C['line']}" stroke-width="2"/>
{text(40, 46, "Gráfico de contribuciones", 26, C['text'], 700)}
{text(width - 40, 46, f"{total} en el último año · racha actual {streak} días", 16, C['muted'], anchor="end")}
{labels}
{weekday_labels}
{cells}
{legend}
"""
    return svg(width, height, body, f"Contribuciones: {total} en el último año")


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    profile = data["profile"]
    days = load_days(data)
    cards = {
        "hero.svg": hero(profile),
        "build.svg": build(profile),
        "brand.svg": brand(profile),
        "learn.svg": learn(profile),
        "activity.svg": activity(days),
        "graph.svg": graph(days),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in cards.items():
        (OUT_DIR / name).write_text(content, encoding="utf-8")
        print(f"{OUT_DIR / name}  {len(content) // 1024} KB")


if __name__ == "__main__":
    main()
