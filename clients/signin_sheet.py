"""Landscape sign-in sheet matching the paper roster staff already print."""

import base64
import csv
from io import BytesIO, StringIO
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
    """Dark wordmark for white paper. The site file is white and prints inverted."""
    global _LOGO_DATA_URI
    if _LOGO_DATA_URI is not None:
        return _LOGO_DATA_URI
    path = Path(settings.BASE_DIR) / 'frontend' / 'public' / 'mhh-logo.png'
    if not path.is_file():
        _LOGO_DATA_URI = ''
        return _LOGO_DATA_URI
    from PIL import Image

    image = Image.open(path).convert('RGBA')
    pixels = image.load()
    width, height = image.size
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 16:
                continue
            is_gold = red > 160 and green > 80 and blue < 120 and red > blue + 40
            if not is_gold:
                pixels[x, y] = (15, 14, 19, alpha)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    _LOGO_DATA_URI = f'data:image/png;base64,{encoded}'
    return _LOGO_DATA_URI


def format_sheet_phone(phone):
    digits = ''.join(character for character in (phone or '') if character.isdigit())
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) == 10:
        return f'{digits[0:3]}-{digits[3:6]}-{digits[6:]}'
    return (phone or '').strip()


def roster_rows_for_session(session):
    enrollments = (
        session.enrollments.select_related('client')
        .exclude(status='cancelled')
        .order_by('client__last_name', 'client__first_name', 'client_id')
    )
    rows = []
    for enrollment in enrollments:
        client = enrollment.client
        rows.append({
            'fn': client.first_name or '',
            'ln': client.last_name or '',
            'phone': format_sheet_phone(client.phone),
            'email': client.email or '',
        })
    return rows


def _sheet_cells(row):
    if row is None:
        values = ('', '', '', '', '', '')
    else:
        values = (row['fn'], row['ln'], row['phone'], row['email'], '', '')
    return ''.join(f'<td>{escape(value)}</td>' for value in values)


def signin_sheet_csv(sessions):
    """One row per person, with blank sign-in and sign-out columns to fill by hand."""
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Class', 'Date', *SHEET_COLUMNS])
    for session in sessions:
        rows = roster_rows_for_session(session)
        blank_count = max(SHEET_MIN_ROWS - len(rows), 0)
        padded = rows + [None] * blank_count
        for row in padded:
            writer.writerow([
                session.template.name,
                session.session_date.isoformat(),
                '' if row is None else row['fn'],
                '' if row is None else row['ln'],
                '' if row is None else row['phone'],
                '' if row is None else row['email'],
                '',
                '',
            ])
    return buffer.getvalue()


def _sheet_section(session, logo_uri):
    dated = sheet_date(session.session_date)
    title = f'{session.template.name} | {dated} | Sign in Sheet'
    rows = roster_rows_for_session(session)
    total = max(SHEET_MIN_ROWS, len(rows))
    body_rows = [
        f'<tr>{_sheet_cells(rows[index] if index < len(rows) else None)}</tr>'
        for index in range(total)
    ]
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
      width: 180px;
      text-align: center;
      background: #fff;
      padding: 6px 8px;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}
    .logo {{ height: 72px; width: auto; display: block; margin: 0 auto; }}
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
