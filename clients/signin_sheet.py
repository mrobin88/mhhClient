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


def format_sheet_phone(phone):
    digits = ''.join(character for character in (phone or '') if character.isdigit())
    if len(digits) == 11 and digits.startswith('1'):
        return f'1 {digits[1:4]} {digits[4:7]} {digits[7:]}'
    if len(digits) == 10:
        return f'{digits[0:3]}-{digits[3:6]}-{digits[6:]}'
    return (phone or '').strip()


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
            'last_name': client.last_name or '',
            'first_name': client.first_name or '',
            'phone': format_sheet_phone(client.phone),
            'email': client.email or '',
        })
    return rows


def signin_sheet_csv(sessions):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        'Class',
        'Date',
        'No.',
        'LN',
        'FN',
        'Phone Number',
        'Email',
        'Signature',
        'Time In',
        'Need Sponsorship',
    ])
    for session in sessions:
        rows = roster_rows_for_session(session)
        blank_count = max(SHEET_MIN_ROWS - len(rows), 0)
        padded = rows + [{'last_name': '', 'first_name': '', 'phone': '', 'email': ''}] * blank_count
        for number, row in enumerate(padded, start=1):
            writer.writerow([
                session.template.name,
                session.session_date.isoformat(),
                number,
                row['last_name'],
                row['first_name'],
                row['phone'],
                row['email'],
                '',
                '',
                '',
            ])
    return buffer.getvalue()


def _sheet_section(session, logo_uri):
    dated = sheet_date(session.session_date)
    title = f'{session.template.name} | {dated} | Sign in Sheet'
    rows = roster_rows_for_session(session)
    total = max(SHEET_MIN_ROWS, len(rows))
    body_rows = []
    for number in range(1, total + 1):
        row = rows[number - 1] if number <= len(rows) else None
        if row:
            cells = (
                f'<td class="num">{number}</td>'
                f'<td>{escape(row["last_name"])}</td>'
                f'<td>{escape(row["first_name"])}</td>'
                f'<td>{escape(row["phone"])}</td>'
                f'<td class="email">{escape(row["email"])}</td>'
                f'<td class="mark">:</td>'
                f'<td class="mark">:</td>'
                f'<td></td>'
            )
        else:
            cells = (
                f'<td class="num">{number}</td>'
                f'<td></td><td></td><td></td><td></td>'
                f'<td class="mark">:</td><td class="mark">:</td><td></td>'
            )
        body_rows.append(f'<tr>{cells}</tr>')
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
            <th class="num">No.</th>
            <th>LN</th>
            <th>FN</th>
            <th>Phone Number</th>
            <th>Email</th>
            <th>Signature</th>
            <th>Time In</th>
            <th>Need Sponsorship</th>
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
