"""Signup list for program managers.

Name, phone, area code, age, email, program, whether they are enrolled,
whether a resume is on file, and the date they signed up. No case notes,
demographics, employment status, or other evaluative fields.
"""

import csv
import logging
import re
from io import StringIO
from pathlib import Path

from django.db.models import Prefetch
from django.utils import timezone
from fpdf import FPDF, FontFace

from .models import Client, Document
from .models_classes import ClassEnrollment
from .phone_utils import phone_digits
from .signin_sheet import sheet_date

COLUMNS = (
    ('name', 'Name'),
    ('phone', 'Phone'),
    ('area_code', 'Area code'),
    ('age', 'Age'),
    ('email', 'Email'),
    ('program', 'Program'),
    ('enrolled', 'Enrolled'),
    ('resume', 'Resume on file'),
    ('signed_up', 'Signed up'),
)

# Relative widths. fpdf scales these to the page.
COLUMN_WIDTHS = (18, 14, 9, 6, 22, 16, 18, 9, 10)

_FONT_DIR = Path(__file__).resolve().parent / 'fonts'
_ACTIVE_CLASS_STATUSES = ('registered', 'attended')


def area_code_from_phone(phone):
    """First three digits of a 10-digit US number. A leading 1 is dropped."""
    digits = phone_digits(phone or '')
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) != 10:
        return ''
    return digits[:3]


def _class_names(client):
    names = []
    seen = set()
    for enrollment in client.class_enrollments.all():
        name = (enrollment.session.template.name or '').strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _in_program(client):
    if client.citybuild_stage in (
        Client.CITYBUILD_STAGE_ENROLLED,
        Client.CITYBUILD_STAGE_ARRIVED,
    ):
        return True
    return client.pit_stop_stage in (
        Client.PIT_STOP_STAGE_ACTIVE_PARTICIPANT,
        Client.PIT_STOP_STAGE_WORKER,
    )


def enrolled_label(client):
    names = _class_names(client)
    if names:
        return 'Yes - ' + '; '.join(names)
    if _in_program(client):
        return 'Yes'
    return 'No'


def resume_on_file_label(client):
    if client.resume:
        return 'Yes'
    documents = getattr(client, 'resume_documents', None)
    if documents is None:
        documents = client.documents.filter(doc_type='resume').exclude(file='')
    return 'Yes' if documents else 'No'


def _signed_up_date(client):
    created = client.created_at
    if created is None:
        return ''
    if timezone.is_aware(created):
        created = timezone.localtime(created)
    return created.strftime('%Y-%m-%d')


def signup_rows(queryset):
    clients = queryset.prefetch_related(
        Prefetch(
            'class_enrollments',
            queryset=ClassEnrollment.objects.filter(
                status__in=_ACTIVE_CLASS_STATUSES,
            ).select_related('session__template').order_by('session__session_date', 'pk'),
        ),
        Prefetch(
            'documents',
            queryset=Document.objects.filter(doc_type='resume').exclude(file=''),
            to_attr='resume_documents',
        ),
    ).order_by('last_name', 'first_name', 'pk')
    rows = []
    for client in clients:
        age = client.age
        rows.append({
            'name': client.full_name,
            'phone': client.phone or '',
            'area_code': area_code_from_phone(client.phone),
            'age': '' if age is None else str(age),
            'email': client.email or '',
            'program': client.get_training_interest_display(),
            'enrolled': enrolled_label(client),
            'resume': resume_on_file_label(client),
            'signed_up': _signed_up_date(client),
        })
    return rows


def list_title(rows):
    programs = {row['program'] for row in rows if row['program']}
    if len(programs) == 1:
        return f'{next(iter(programs))} signup list'
    return 'Signup list'


def signup_filename(rows, extension, when=None):
    when = timezone.localtime(when) if when is not None else timezone.localtime()
    stamp = when.strftime('%Y%m%d')
    programs = {row['program'] for row in rows if row['program']}
    if len(programs) == 1:
        slug = re.sub(r'[^a-z0-9]+', '_', next(iter(programs)).lower()).strip('_')
        return f'signup_list_{slug}_{stamp}.{extension}'
    return f'signup_list_{stamp}.{extension}'


def signup_list_csv(rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([label for _key, label in COLUMNS])
    for row in rows:
        writer.writerow([row[key] for key, _label in COLUMNS])
    return buffer.getvalue()


class _SignupListPDF(FPDF):
    def __init__(self, title, printed_on, people_label):
        super().__init__(orientation='L', unit='mm', format='Letter')
        self.banner = f'{title}  |  {printed_on}  |  {people_label}'
        self.add_font('DejaVu', '', str(_FONT_DIR / 'DejaVuSans.ttf'))
        self.add_font('DejaVu', 'B', str(_FONT_DIR / 'DejaVuSans-Bold.ttf'))
        self.set_auto_page_break(auto=True, margin=12)
        self.set_margins(8, 22, 8)
        self.set_title(title)
        self.set_author('Mission Hiring Hall')

    def header(self):
        self.set_fill_color(15, 14, 19)
        self.rect(0, 0, self.w, 16, style='F')
        self.set_fill_color(232, 146, 36)
        self.rect(0, 16, self.w, 1.3, style='F')
        self.set_text_color(232, 146, 36)
        self.set_font('DejaVu', 'B', 11)
        self.text(8, 7, 'Mission Hiring Hall')
        self.set_text_color(255, 255, 255)
        self.set_font('DejaVu', '', 8)
        self.text(8, 13, self.banner)
        self.set_text_color(20, 20, 20)

    def footer(self):
        self.set_font('DejaVu', '', 8)
        self.set_text_color(90, 90, 90)
        label = f'Contact list for program staff    Page {self.page_no()}'
        self.text(self.w - self.get_string_width(label) - 8, self.h - 6, label)


def signup_list_pdf(rows):
    logging.getLogger('fontTools').setLevel(logging.WARNING)
    count = len(rows)
    people = '1 person' if count == 1 else f'{count} people'
    pdf = _SignupListPDF(list_title(rows), sheet_date(timezone.localdate()), people)
    pdf.add_page()
    pdf.set_font('DejaVu', '', 8)
    if not rows:
        pdf.set_xy(pdf.l_margin, 24)
        pdf.cell(0, 8, 'No signups selected.')
        return bytes(pdf.output())

    headings = FontFace(
        family='DejaVu',
        emphasis='BOLD',
        size_pt=8,
        color=(255, 255, 255),
        fill_color=(15, 14, 19),
    )
    table_rows = [[label for _key, label in COLUMNS]]
    table_rows.extend([row[key] for key, _label in COLUMNS] for row in rows)
    with pdf.table(
        rows=table_rows,
        col_widths=COLUMN_WIDTHS,
        headings_style=headings,
        text_align='LEFT',
        line_height=4.2,
        padding=1.2,
        min_row_height=7,
        repeat_headings=1,
    ):
        pass
    return bytes(pdf.output())
