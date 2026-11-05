"""Landscape sign-in sheet matching the paper roster staff already print."""

import base64
import csv
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.utils.html import escape

SHEET_MIN_ROWS = 28

_LOGO_DATA_URI = None


def sheet_date(value):
    """October 15th, 2026 — the date line on the paper sign-in sheet."""
    day = value.day
    if 10 <= day % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
    return f'{value.strftime("%B")} {day}{suffix}, {value.year}'


SHEET_COLUMNS = ('FN', 'LN', 'Phone', 'Email', 'Sign in', 'Sign out')


def _logo_data_uri():
    global _LOGO_DATA_URI
    if _LOGO_DATA_URI is not None:
        return _LOGO_DATA_URI
    path = Path(settings.BASE_DIR) / 'frontend' / 'public' / 'mhh-logo.png'
    if path.is_file():
        encoded = base64.b64encode(path.read_bytes()).decode('ascii')
        _LOGO_DATA_URI = f'data:image/png;base64,{encoded}'
    else:
        _LOGO_DATA_URI = ''
    return _LOGO_DATA_URI


def signin_sheet_csv(sessions):
    """Blank sign-in rows. Names are written on the paper, not printed from the roster."""
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Class', 'Date', *SHEET_COLUMNS])
    for session in sessions:
        for _number in range(SHEET_MIN_ROWS):
            writer.writerow([
                session.template.name,
                session.session_date.isoformat(),
                '',
                '',
                '',
                '',
                '',
                '',
            ])
    return buffer.getvalue()


def _sheet_section(session, logo_uri):
    dated = sheet_date(session.session_date)
    title = f'{session.template.name} | {dated} | Sign in Sheet'
    blank = '<td></td>' * len(SHEET_COLUMNS)
    body_rows = [f'<tr>{blank}</tr>' for _number in range(SHEET_MIN_ROWS)]
    headers = ''.join(f'<th>{escape(label)}</th>' for label in SHEET_COLUMNS)
    logo_html = (
        f'<img src="{logo_uri}" alt="Mission Hiring Hall" class="logo" />'
        if logo_uri
        else '<div class="logo-fallback">MISSION<br>HIRING<br>HALL</div>'
    )
    return f'''
    <section class="sheet">
      <table class="mast">
        <tr>
          <td class="logo-cell" rowspan="2">{logo_html}</td>
          <td class="title">{escape(title)}</td>
        </tr>
        <tr>
          <td class="date-line">{escape(dated)}</td>
        </tr>
        <tr>
          <td class="client-name" colspan="2">Client Name</td>
        </tr>
      </table>
      <table class="grid">
        <thead>
          <tr>
            {headers}
          </tr>
        </thead>
        <tbody>
          {''.join(body_rows)}
        </tbody>
      </table>
    </section>
    '''


def render_signin_sheets(sessions):
    logo_uri = _logo_data_uri()
    sections = ''.join(_sheet_section(session, logo_uri) for session in sessions)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Sign in Sheet</title>
  <style>
    @page {{ size: letter landscape; margin: 0.35in; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: #111;
      font-family: Arial, Helvetica, sans-serif;
      background: #fff;
    }}
    .print-bar {{
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin: 0 0 10px;
    }}
    .print-bar button {{
      font: 700 14px Arial, sans-serif;
      background: #0f0e13;
      color: #fff;
      border: 0;
      padding: 8px 14px;
      cursor: pointer;
    }}
    .sheet {{ page-break-after: always; }}
    .sheet:last-child {{ page-break-after: auto; }}
    table {{ width: 100%; border-collapse: collapse; }}
    .mast td, .grid th, .grid td {{
      border: 1px solid #111;
    }}
    .logo-cell {{
      width: 210px;
      text-align: center;
      background: #0f0e13;
      padding: 6px 8px;
    }}
    .logo {{ height: 58px; width: auto; display: block; margin: 0 auto; }}
    .logo-fallback {{
      color: #e89224;
      font-weight: 800;
      letter-spacing: 0.04em;
      line-height: 1.15;
      font-size: 14px;
    }}
    .title {{
      text-align: right;
      font-weight: 700;
      font-size: 15px;
      padding: 8px 10px;
    }}
    .date-line {{
      text-align: center;
      font-weight: 700;
      font-size: 14px;
      padding: 6px 10px;
    }}
    .client-name {{
      text-align: center;
      font-weight: 700;
      font-size: 14px;
      padding: 6px;
    }}
    .grid th {{
      font-size: 11px;
      font-weight: 700;
      text-align: center;
      padding: 4px 3px;
      background: #fff;
    }}
    .grid td {{
      font-size: 11px;
      height: 22px;
      padding: 1px 4px;
      vertical-align: middle;
    }}
    .num {{ width: 36px; text-align: center; }}
    .email {{ font-size: 10px; }}
    .mark {{
      text-align: center;
      color: #222;
      width: 92px;
    }}
    @media print {{
      .print-bar {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="print-bar">
    <button type="button" onclick="window.print()">Print roster</button>
  </div>
  {sections}
  <script>window.addEventListener('load', function () {{ window.print(); }});</script>
</body>
</html>
'''
