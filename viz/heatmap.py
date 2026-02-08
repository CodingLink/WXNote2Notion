from __future__ import annotations

import calendar
from datetime import date, timedelta
from pathlib import Path
from typing import Dict

# Blue monochrome palette (0 activity -> High activity)
PALETTE = ["#ebedf0", "#c6dbef", "#6baed6", "#3182bd", "#08519c"]


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
    # 1. Determine date range
    first_day = date(year, 1, 1)
    last_day = date(year, 12, 31)
    
    # 2. Align start to the Monday of the first week
    # weekday(): 0=Mon, ..., 6=Sun
    # If Jan 1 is Mon(0), start=Jan 1. If Jan 1 is Tue(1), start=Dec 31 (prev year).
    start = first_day - timedelta(days=first_day.weekday())
    
    # 3. Align end to the Sunday of the last week
    end = last_day
    while end.weekday() != 6:
        end += timedelta(days=1)

    # SVG Constants
    CELL_SIZE = 10
    CELL_GAP = 2
    WEEK_WIDTH = CELL_SIZE + CELL_GAP
    TEXT_HEIGHT = 15  # For month labels
    
    rects = []
    max_count = max(daily_counts.values()) if daily_counts else 0
    
    day = start
    week = 0
    
    # Track month positions (x-coordinate)
    # Mapping: month_index (1-12) -> first x-coordinate
    month_initial_x: Dict[int, int] = {}

    while day <= end:
        # Calculate positions
        # Row: Mon=0 ... Sun=6
        row = day.weekday()
        x = week * WEEK_WIDTH
        y = row * WEEK_WIDTH + TEXT_HEIGHT  # Offset by header height
        
        # Color & Data
        count = daily_counts.get(day, 0)
        color = _color_for(count, max_count)
        
        # Capture first occurrence of a month to place label
        if day.year == year and day.day <= 7: 
            if day.day == 1:
                month_initial_x[day.month] = x
        
        rects.append(
            f'<rect class="day-cell" width="{CELL_SIZE}" height="{CELL_SIZE}" '
            f'x="{x}" y="{y}" rx="2" ry="2" fill="{color}" '
            f'data-date="{day.isoformat()}" data-count="{count}" '
            f'data-date-readable="{day.strftime("%B %d")}"></rect>'
        )
        
        if row == 6: # Sunday, end of column
            week += 1
        day += timedelta(days=1)

    # Generate Month Labels
    month_labels = []
    for m in range(1, 13):
        x_pos = month_initial_x.get(m)
        if x_pos is not None:
            month_name = calendar.month_abbr[m]
            month_labels.append(
                f'<text x="{x_pos}" y="{TEXT_HEIGHT - 5}" font-family="sans-serif" font-size="10" fill="#767676">{month_name}</text>'
            )

    width = (week + 1) * WEEK_WIDTH + 10
    height = 7 * WEEK_WIDTH + TEXT_HEIGHT + 10
    
    svg_content = "".join(month_labels + rects)

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" role="img" aria-label="Reading activity heatmap">'
        f'<style>text {{ dominant-baseline: auto; }}</style>'
        f'<g transform="translate(14, 0)">{svg_content}</g>'
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
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
    
    /* Tooltip Styles */
    #tooltip {{
      position: absolute;
      display: none;
      background: #ffffff;
      color: #24292f;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      border: 1px solid rgba(0,0,0,0.1);
      pointer-events: none;
      z-index: 100;
      white-space: nowrap;
    }}
    
    /* Hover effect on cells */
    rect.day-cell {{
        transition: stroke 0.1s;
    }}
    rect.day-cell:hover {{
        stroke: #555;
        stroke-width: 1px;
    }}

    @media (prefers-color-scheme: dark) {{
      .card {{ background: #0d1117; border-color: #30363d; }}
      h1 {{ color: #c9d1d9; }}
      .legend {{ color: #8b949e; }}
      select {{ background-color: #21262d; border-color: #363b42; color: #c9d1d9; }}
      #tooltip {{ background: #21262d; color: #c9d1d9; border-color: #30363d; }}
    }}
  </style>
  <script>
    function changeYear(select) {{
      const year = select.value;
      document.querySelectorAll('.heatmap-wrapper').forEach(el => el.style.display = 'none');
      document.getElementById('year-' + year).style.display = 'block';
    }}

    document.addEventListener('DOMContentLoaded', () => {{
      const tooltip = document.getElementById('tooltip');
      const cells = document.querySelectorAll('.day-cell');

      cells.forEach(cell => {{
        cell.addEventListener('mouseenter', (e) => {{
          const dateStr = cell.getAttribute('data-date-readable');
          const count = cell.getAttribute('data-count');
          const unit = count == 1 ? 'note' : 'notes';
          
          tooltip.innerHTML = `<strong>${{dateStr}}</strong><br>${{count}} ${{unit}}`;
          tooltip.style.display = 'block';
          
          // Initial position required to calculate dimensions
          const rect = cell.getBoundingClientRect();
          const tooltipRect = tooltip.getBoundingClientRect();
          
          // Center above the cell
          let top = rect.top + window.scrollY - tooltipRect.height - 8;
          let left = rect.left + window.scrollX + (rect.width / 2) - (tooltipRect.width / 2);
          
          tooltip.style.top = `${{top}}px`;
          tooltip.style.left = `${{left}}px`;
        }});

        cell.addEventListener('mouseleave', () => {{
          tooltip.style.display = 'none';
        }});
      }});
    }});
  </script>
</head>
<body>
  <div id="tooltip"></div>
  <div class="card">
    <div class="header">
      <h1>Reading Contributions</h1>
      <select onchange="changeYear(this)">
        {options_html}
      </select>
    </div>
    
    {''.join(containers_html)}
    
    <div class="legend">
      <span>Less</span>
      {''.join([f'<span class="box" style="background:{c}"></span>' for c in PALETTE])}
      <span>More</span>
    </div>
  </div>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html, encoding="utf-8")
