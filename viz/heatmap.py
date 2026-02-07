from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path
from typing import Dict

PALETTE = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]


def _color_for(count: int, max_count: int) -> str:
    if max_count <= 0:
        return PALETTE[0]
    if count <= 0:
        return PALETTE[0]
    # bucket into 4 levels
    ratio = count / max_count
    if ratio > 0.75:
        return PALETTE[4]
    if ratio > 0.5:
        return PALETTE[3]
    if ratio > 0.25:
        return PALETTE[2]
    return PALETTE[1]


def generate_heatmap_svg(daily_counts: Dict[date, int], year: int) -> str:
    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)
    # Align to Sunday start
    start = first_day - timedelta(days=first_day.weekday() + 1 if first_day.weekday() != 6 else 0)
    end = last_day
    while end.weekday() != 6:
        end += timedelta(days=1)

    day = start
    week = 0
    rects = []
    max_count = max(daily_counts.values()) if daily_counts else 0
    
    # SVG Constants
    CELL_SIZE = 10
    CELL_GAP = 2
    WEEK_WIDTH = CELL_SIZE + CELL_GAP
    
    while day <= end:
        color = _color_for(daily_counts.get(day, 0), max_count)
        x = week * WEEK_WIDTH
        y = day.weekday() * WEEK_WIDTH
        # GitHub style: 0=Sunday. python day.weekday(): 0=Monday, 6=Sunday.
        # We want Sunday at top (y=0).
        # Adjust day.weekday() to Sunday=0 map: 6->0, 0->1, 1->2 ...
        week_day_idx = (day.weekday() + 1) % 7
        y = week_day_idx * WEEK_WIDTH
        
        rects.append(
            f'<rect width="{CELL_SIZE}" height="{CELL_SIZE}" x="{x}" y="{y}" rx="2" ry="2" fill="{color}" data-date="{day.isoformat()}" data-count="{daily_counts.get(day, 0)}">'
            f'<title>{daily_counts.get(day, 0)} notes on {day.isoformat()}</title>'
            f'</rect>'
        )
        
        if week_day_idx == 6: # Saturday, end of column
            week += 1
        day += timedelta(days=1)

    width = (week + 1) * WEEK_WIDTH + 10
    height = 7 * WEEK_WIDTH + 10
    
    label_days = ['Mon', 'Wed', 'Fri']
    # Simplified without axis labels for now to keep SVG robust
    
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="Reading activity heatmap">'
        f"<style>rect {{ shape-rendering: geometricPrecision; }} rect:hover {{ stroke: #555; stroke-width: 1px; }}</style>"
        f'<g transform="translate(4, 4)">{"".join(rects)}</g>'
        "</svg>"
    )
    return svg


def write_heatmap(daily_counts: Dict[date, int], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine all years from data
    years = sorted(list({d.year for d in daily_counts.keys()}), reverse=True)
    if not years:
        years = [date.today().year]
    
    # Generate SVGs
    svgs = {}
    for y in years:
        year_counts = {d: c for d, c in daily_counts.items() if d.year == y}
        svgs[y] = generate_heatmap_svg(year_counts, y)
    
    # Save the latest year as default heatmap.svg
    latest_year = years[0]
    (out_dir / "heatmap.svg").write_text(svgs[latest_year], encoding="utf-8")

    # Generate options HTML
    options_html = "".join([f'<option value="{y}">{y}</option>' for y in years])
    
    # Generate containers
    containers_html = []
    for y in years:
        display_style = "block" if y == latest_year else "none"
        containers_html.append(f'<div id="year-{y}" class="heatmap-wrapper" style="display: {display_style};">{svgs[y]}</div>')
    
    html = f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>WeChat Read Heatmap</title>
  <style>
    body {{ 
      font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;
      display: flex; 
      align-items: center; 
      justify-content: center; 
      min-height: 100vh;
      margin: 0;
      background-color: transparent; 
    }}
    .card {{ 
      background: #ffffff; 
      padding: 16px; 
      border: 1px solid #d0d7de; 
      border-radius: 6px; 
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      max-width: 100%;
      overflow-x: auto;
      position: relative;
    }}
    .header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }}
    h1 {{ 
      margin: 0; 
      font-size: 14px; 
      font-weight: 600; 
      color: #24292f; 
    }}
    select {{
      font-size: 12px;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid #d0d7de;
      background-color: #f6f8fa;
      color: #24292f;
      outline: none;
    }}
    .legend {{ 
      display: flex; 
      gap: 4px; 
      align-items: center; 
      margin-top: 8px; 
      font-size: 12px; 
      color: #57606a; 
      justify-content: flex-end;
    }}
    .legend span.box {{ 
      width: 10px; 
      height: 10px; 
      border-radius: 2px; 
      display: inline-block; 
    }}
    @media (prefers-color-scheme: dark) {{
      .card {{ background: #0d1117; border-color: #30363d; }}
      h1 {{ color: #c9d1d9; }}
      .legend {{ color: #8b949e; }}
      select {{ background-color: #21262d; border-color: #363b42; color: #c9d1d9; }}
    }}
  </style>
  <script>
    function changeYear(select) {{
      const year = select.value;
      document.querySelectorAll('.heatmap-wrapper').forEach(el => el.style.display = 'none');
      document.getElementById('year-' + year).style.display = 'block';
    }}
  </script>
</head>
<body>
  <div class=\"card\">
    <div class=\"header\">
      <h1>Reading Contributions</h1>
      <select onchange=\"changeYear(this)\">
        {options_html}
      </select>
    </div>
    
    {''.join(containers_html)}
    
    <div class=\"legend\">
      <span>Less</span>
      {''.join([f'<span class="box" style="background:{c}"></span>' for c in PALETTE])}
      <span>More</span>
    </div>
  </div>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
