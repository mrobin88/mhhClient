"""
Aggregate program impact report for SF OEWD.

There is no enrollment table. One Client row is one person in one program
(`training_interest`). The service start is `program_start_date` when staff
recorded it, otherwise the sign-up timestamp in America/Los_Angeles. The only
exit date is `program_completed_date`. Stage flags are not dates.

Demographics use fields that already exist. Household income is not stored.
Neighborhood is the intake choice, not a ZIP lookup.

Activity after sign-up is a case note (including lobby check-in), class
attendance, a worker clock-in, or worker daily feedback. "Recently active"
counts served clients with any of those in the 90 days ending on the period
end date.
"""
from calendar import monthrange
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
import csv
import io

from django.db.models import (
    Case,
    CharField,
    Count,
    DateField,
    ExpressionWrapper,
    F,
    IntegerField,
    Q,
    Value,
    When,
)
from django.db.models.functions import Coalesce, ExtractDay, ExtractMonth, ExtractYear, Trim, TruncDate, TruncMonth
from django.utils import timezone

from .models import CaseNote, Client, JobPlacement
from .models_classes import ClassEnrollment
from .models_extensions import WorkerDailyFeedback, WorkerTimePunch

ORG_NAME = 'Mission Hiring Hall'
REPORT_TITLE = 'Program Impact Report'
PREPARED_FOR = 'SF OEWD'
SMALL_CELL_THRESHOLD = 5
RECENT_ACTIVITY_DAYS = 90
OTHER_LABEL = 'Other'
OUTSIDE_SF_LABEL = 'Outside San Francisco'

# USPS ZIP codes for the City and County of San Francisco, including Treasure
# Island (94130) and the Presidio (94129). 94128 is the airport in San Mateo
# County and stays outside the city.
SF_ZIP_CODES = frozenset({
    '94102', '94103', '94104', '94105', '94107', '94108', '94109', '94110',
    '94111', '94112', '94114', '94115', '94116', '94117', '94118', '94121',
    '94122', '94123', '94124', '94127', '94129', '94130', '94131', '94132',
    '94133', '94134', '94143', '94158',
})

PRESET_CHOICES = (
    ('this_month', 'This month'),
    ('last_quarter', 'Last quarter'),
    ('fiscal_ytd', 'Fiscal YTD'),
    ('calendar_year', 'Calendar year'),
    ('last_12', 'Last 12 months'),
    ('custom', 'Custom'),
)
PRESET_IDS = {key for key, _label in PRESET_CHOICES}

GENDER_LABELS = {
    'F': 'Female',
    'M': 'Male',
    'NB': 'Non-binary',
    'O': 'Other',
    'P': 'Declined/Unknown',
    '': 'Declined/Unknown',
}
GENDER_ORDER = ('Female', 'Male', 'Non-binary', 'Other', 'Declined/Unknown')
AGE_ORDER = ('<18', '18-24', '25-34', '35-44', '45-54', '55-64', '65+', 'Unknown')
DONUT_COLORS = ('#134e4a', '#0f766e', '#0d9488', '#14b8a6', '#5eead4', '#99f6e4')


class ReportPeriodError(ValueError):
    pass


def age_bin(dob, as_of):
    """Age on as_of. Birthday that day counts as having reached that age."""
    if not dob:
        return 'Unknown'
    age = as_of.year - dob.year - ((as_of.month, as_of.day) < (dob.month, dob.day))
    if age < 0:
        return 'Unknown'
    if age < 18:
        return '<18'
    if age <= 24:
        return '18-24'
    if age <= 34:
        return '25-34'
    if age <= 44:
        return '35-44'
    if age <= 54:
        return '45-54'
    if age <= 64:
        return '55-64'
    return '65+'


def normalize_zip(value):
    digits = ''.join(character for character in (value or '') if character.isdigit())
    if len(digits) < 5:
        return None
    return digits[:5]


def bucket_zips(raw_counts):
    """Group DB zip totals. Non-SF ZIPs become one bar. Blank ZIPs are omitted."""
    bucketed = {}
    for raw, count in raw_counts.items():
        if not count:
            continue
        normalized = normalize_zip(raw)
        if not normalized:
            continue
        label = normalized if normalized in SF_ZIP_CODES else OUTSIDE_SF_LABEL
        bucketed[label] = bucketed.get(label, 0) + count
    return bucketed


def previous_period(start_date, end_date):
    length = (end_date - start_date).days + 1
    prior_end = start_date - timedelta(days=1)
    prior_start = prior_end - timedelta(days=length - 1)
    return prior_start, prior_end


def date_range_for_preset(preset, today):
    if preset == 'this_month':
        return date(today.year, today.month, 1), today
    if preset == 'last_quarter':
        return _last_completed_quarter(today)
    if preset == 'fiscal_ytd':
        fiscal_year = today.year if today.month >= 7 else today.year - 1
        return date(fiscal_year, 7, 1), today
    if preset == 'calendar_year':
        return date(today.year, 1, 1), today
    if preset == 'last_12':
        return _add_years(today, -1) + timedelta(days=1), today
    raise ReportPeriodError('Choose a date range.')


def resolve_report_period(params, today=None):
    today = today or timezone.localdate()
    preset = (params.get('preset') or '').strip()
    program_id = (params.get('program') or '').strip()
    if program_id and program_id not in dict(Client.TRAINING_INTEREST_CHOICES):
        raise ReportPeriodError('That program is not in the system.')
    if not preset:
        preset = 'custom' if (params.get('start_date') or params.get('end_date')) else 'fiscal_ytd'
    if preset == 'custom':
        start_date = _parse_date(params.get('start_date'))
        end_date = _parse_date(params.get('end_date'))
        if start_date is None or end_date is None:
            raise ReportPeriodError('Enter both a start date and an end date.')
        if start_date > end_date:
            raise ReportPeriodError('The start date has to be on or before the end date.')
        return start_date, end_date, 'custom', program_id
    if preset not in PRESET_IDS:
        preset = 'fiscal_ytd'
    start_date, end_date = date_range_for_preset(preset, today)
    return start_date, end_date, preset, program_id


def suppress_categories(label_counts, *, order=None, top_n=None):
    """
    Hide groups smaller than SMALL_CELL_THRESHOLD by folding them into Other.

    Displayed percents use only groups that still show an exact count, so a
    reader cannot recover a hidden group by subtracting from 100.
    """
    counts = {}
    for label, count in label_counts.items():
        if count:
            counts[label] = counts.get(label, 0) + int(count)

    if top_n is not None:
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        counts = dict(ranked[:top_n])
        tail = sum(count for _label, count in ranked[top_n:])
        if tail:
            counts[OTHER_LABEL] = counts.get(OTHER_LABEL, 0) + tail

    rolled = counts.pop(OTHER_LABEL, 0)
    kept = {}
    for label, count in counts.items():
        if count < SMALL_CELL_THRESHOLD:
            rolled += count
        else:
            kept[label] = count
    if rolled:
        kept[OTHER_LABEL] = rolled

    ordered = _order_labels(kept, order)
    exact_total = sum(count for _label, count in ordered if count >= SMALL_CELL_THRESHOLD)
    exact_counts = [count if count >= SMALL_CELL_THRESHOLD else 0 for _label, count in ordered]
    percents = _largest_remainder(exact_counts, exact_total)
    max_exact = max(exact_counts) if any(exact_counts) else 0

    rows = []
    for (label, count), percent in zip(ordered, percents):
        suppressed = count < SMALL_CELL_THRESHOLD
        rows.append({
            'label': label,
            'count_display': f'<{SMALL_CELL_THRESHOLD}' if suppressed else str(count),
            'percent_display': '' if suppressed or exact_total == 0 else f'{percent}%',
            'bar_width': 0 if suppressed or max_exact == 0 else max(1, round(count / max_exact * 100)),
            'suppressed': suppressed,
        })
    return rows


def series_rows(ordered_pairs):
    """Time buckets stay in order. A month under the threshold shows <5, not Other."""
    exact_total = sum(count for _label, count in ordered_pairs if count >= SMALL_CELL_THRESHOLD)
    exact_counts = [count if count >= SMALL_CELL_THRESHOLD else 0 for _label, count in ordered_pairs]
    percents = _largest_remainder(exact_counts, exact_total)
    max_exact = max(exact_counts) if any(exact_counts) else 0
    rows = []
    for (label, count), percent in zip(ordered_pairs, percents):
        suppressed = 0 < count < SMALL_CELL_THRESHOLD
        if count == 0:
            count_display = '0'
            percent_display = '0%' if exact_total else '0%'
            bar_width = 0
        elif suppressed:
            count_display = f'<{SMALL_CELL_THRESHOLD}'
            percent_display = ''
            bar_width = 0
        else:
            count_display = str(count)
            percent_display = f'{percent}%' if exact_total else ''
            bar_width = max(1, round(count / max_exact * 100)) if max_exact else 0
        rows.append({
            'label': label,
            'count_display': count_display,
            'percent_display': percent_display,
            'bar_width': bar_width,
            'suppressed': suppressed,
        })
    return rows


def get_aggregate_report(start_date, end_date, program_id=None):
    """All headline numbers, charts, and the completeness note for one period."""
    if start_date > end_date:
        raise ValueError('start_date must be on or before end_date')
    program_id = program_id or None
    if program_id and program_id not in dict(Client.TRAINING_INTEREST_CHOICES):
        raise ValueError('Unknown program')

    served, new = _cohorts(start_date, end_date, program_id)
    prior_start, prior_end = previous_period(start_date, end_date)
    prior_served, prior_new = _cohorts(prior_start, prior_end, program_id)

    current_kpis = _kpi_numbers(served, new, end_date)
    prior_kpis = _kpi_numbers(prior_served, prior_new, prior_end)
    completeness = _completeness(served, start_date, end_date)
    generated_at = timezone.now()

    report = {
        'org_name': ORG_NAME,
        'report_title': REPORT_TITLE,
        'prepared_for': PREPARED_FOR,
        'start_date': start_date,
        'end_date': end_date,
        'prior_start': prior_start,
        'prior_end': prior_end,
        'range_label': f'{_long_date(start_date)} – {_long_date(end_date)}',
        'prior_range_label': f'{_long_date(prior_start)} – {_long_date(prior_end)}',
        'program_id': program_id or '',
        'program_label': dict(Client.TRAINING_INTEREST_CHOICES).get(program_id, 'All programs'),
        'generated_at': generated_at,
        'generated_label': _long_date(timezone.localtime(generated_at).date()),
        'data_as_of_label': _timestamp_label(generated_at),
        'kpis': _kpi_cards(current_kpis, prior_kpis),
        'exits_recorded': completeness['exits_recorded'],
        'job_placements': _job_placements(served, start_date, end_date),
        'completeness': completeness,
        'suppression_note': (
            f'Groups with fewer than {SMALL_CELL_THRESHOLD} clients are shown as '
            f'<{SMALL_CELL_THRESHOLD}, left out of the percentages, and combined into Other. '
            'Months stay in calendar order; a month under that count is shown as '
            f'<{SMALL_CELL_THRESHOLD} and is not combined.'
        ),
        'empty_message': '',
        'sections': [],
    }
    if current_kpis['unduplicated'] == 0 and current_kpis['new_enrollments'] == 0:
        report['empty_message'] = 'No one in this period.'
        return report

    report['sections'] = _sections(served, new, start_date, end_date, current_kpis['new_enrollments'])
    return report


def render_aggregate_csv(report):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['Organization', report['org_name']])
    writer.writerow(['Report', report['report_title']])
    writer.writerow(['Prepared for', report['prepared_for']])
    writer.writerow(['Start date', report['start_date'].isoformat()])
    writer.writerow(['End date', report['end_date'].isoformat()])
    writer.writerow(['Comparison period', report['prior_range_label']])
    writer.writerow(['Program', report['program_label']])
    writer.writerow(['Generated', report['data_as_of_label']])
    writer.writerow([])
    writer.writerow(['Section', 'Label', 'Count', 'Percent', 'Change vs prior period'])
    for kpi in report['kpis']:
        writer.writerow(['Summary', kpi['label'], kpi['count'], '', kpi['change_display'] or ''])
    writer.writerow(['Summary', 'Finished', report['exits_recorded'], '', ''])
    writer.writerow(['Summary', 'Got a job', report['job_placements'], '', ''])
    for section in report['sections']:
        for row in section['rows']:
            writer.writerow([
                section['title'],
                row['label'],
                row['count_display'],
                row['percent_display'],
                '',
            ])
    writer.writerow([])
    writer.writerow(['Note', report['completeness']['text']])
    writer.writerow(['Note', report['suppression_note']])
    return buffer.getvalue()


def build_report_page_context(params, today=None):
    raw_start = (params.get('start_date') or '').strip()
    raw_end = (params.get('end_date') or '').strip()
    raw_program = (params.get('program') or '').strip()
    raw_preset = (params.get('preset') or '').strip()
    context = {
        'org_name': ORG_NAME,
        'report_title': REPORT_TITLE,
        'prepared_for': PREPARED_FOR,
        'programs': [{'id': key, 'label': label} for key, label in Client.TRAINING_INTEREST_CHOICES],
        'presets': [{'id': key, 'label': label} for key, label in PRESET_CHOICES if key != 'custom'],
        'active_preset': raw_preset if raw_preset in PRESET_IDS else 'fiscal_ytd',
        'selected_program': raw_program,
        'start_value': raw_start,
        'end_value': raw_end,
        'fiscal_note': 'Fiscal year starts July 1.',
        'error': None,
        'report': None,
        'querystring': '',
    }
    try:
        start_date, end_date, preset, program_id = resolve_report_period(params, today=today)
    except ReportPeriodError as exc:
        context['error'] = str(exc)
        if raw_preset == 'custom' or raw_start or raw_end:
            context['active_preset'] = 'custom'
        return context

    report = get_aggregate_report(start_date, end_date, program_id or None)
    context.update(
        report=report,
        active_preset=preset,
        selected_program=program_id,
        start_value=start_date.isoformat(),
        end_value=end_date.isoformat(),
        querystring=urlencode({
            'preset': preset,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'program': program_id,
        }),
    )
    return context


def _cohorts(start_date, end_date, program_id):
    base = Client.objects.annotate(service_start=_service_start_expression())
    if program_id:
        base = base.filter(training_interest=program_id)
    served = base.filter(service_start__lte=end_date).filter(
        Q(program_completed_date__isnull=True) | Q(program_completed_date__gte=start_date)
    )
    new = base.filter(service_start__gte=start_date, service_start__lte=end_date)
    return served, new


def _service_start_expression():
    return Coalesce(
        F('program_start_date'),
        TruncDate('created_at'),
        output_field=DateField(),
    )


def _kpi_numbers(served, new, end_date):
    return {
        'unduplicated': served.count(),
        'new_enrollments': new.count(),
        'programs': served.order_by().values('training_interest').distinct().count(),
        'recently_active': _recently_active_count(served, end_date),
    }


def _kpi_cards(current, prior):
    specs = (
        (
            'unduplicated',
            'People served',
            '',
        ),
        (
            'new_enrollments',
            'Started',
            '',
        ),
        (
            'programs',
            'Programs',
            '',
        ),
        (
            'recently_active',
            'Seen in the last 90 days',
            '',
        ),
    )
    cards = []
    for key, label, hint in specs:
        cards.append({
            'key': key,
            'label': label,
            'hint': hint,
            'count': current[key],
            'prior': prior[key],
            'change_display': _format_change(current[key], prior[key]),
        })
    return cards


def _recently_active_count(served, end_date):
    window_start = end_date - timedelta(days=RECENT_ACTIVITY_DAYS)
    note_ids = CaseNote.objects.filter(
        note_date__gte=window_start,
        note_date__lte=end_date,
    ).values('client_id')
    class_ids = ClassEnrollment.objects.filter(
        status='attended',
        session__session_date__gte=window_start,
        session__session_date__lte=end_date,
    ).values('client_id')
    punch_ids = WorkerTimePunch.objects.filter(
        clock_in_at__date__gte=window_start,
        clock_in_at__date__lte=end_date,
    ).values('worker_account__client_id')
    feedback_ids = WorkerDailyFeedback.objects.filter(
        feedback_date__gte=window_start,
        feedback_date__lte=end_date,
    ).values('worker_account__client_id')
    return served.filter(
        Q(pk__in=note_ids)
        | Q(pk__in=class_ids)
        | Q(pk__in=punch_ids)
        | Q(pk__in=feedback_ids)
    ).count()


def _completeness(served, start_date, end_date):
    stats = served.annotate(zip_trimmed=Trim('zip_code')).aggregate(
        total=Count('pk'),
        no_exit=Count('pk', filter=Q(program_completed_date__isnull=True)),
        missing_zip=Count('pk', filter=Q(zip_trimmed__isnull=True) | Q(zip_trimmed='')),
        missing_dob=Count('pk', filter=Q(dob__isnull=True)),
        missing_gender=Count('pk', filter=Q(gender__isnull=True) | Q(gender='')),
        missing_start=Count('pk', filter=Q(program_start_date__isnull=True)),
        exits_recorded=Count(
            'pk',
            filter=Q(program_completed_date__gte=start_date, program_completed_date__lte=end_date),
        ),
    )
    total = stats['total'] or 0
    percents = {
        'no_exit_pct': _share(stats['no_exit'], total),
        'missing_zip_pct': _share(stats['missing_zip'], total),
        'missing_dob_pct': _share(stats['missing_dob'], total),
        'missing_gender_pct': _share(stats['missing_gender'], total),
        'missing_program_start_pct': _share(stats['missing_start'], total),
    }
    if total == 0:
        text = 'No one in this period.'
    else:
        text = (
            f"{percents['no_exit_pct']}% have no end date on file. "
            f"{percents['missing_zip_pct']}% are missing a ZIP code, "
            f"{percents['missing_dob_pct']}% are missing a birth date, "
            f"and {percents['missing_gender_pct']}% are missing gender."
        )
    return {
        'served': total,
        'exits_recorded': stats['exits_recorded'] or 0,
        'text': text,
        **percents,
    }


def _job_placements(served, start_date, end_date):
    served_ids = served.order_by().values('pk')
    placement_ids = JobPlacement.objects.filter(
        start_date__gte=start_date,
        start_date__lte=end_date,
        client_id__in=served_ids,
    ).values('client_id')
    return served.filter(
        Q(pk__in=placement_ids)
        | Q(job_placement_date__gte=start_date, job_placement_date__lte=end_date)
    ).count()


def _sections(served, new, start_date, end_date, new_count):
    gender_rows = suppress_categories(
        _relabel(_grouped(served, 'gender'), GENDER_LABELS, 'Declined/Unknown'),
        order=GENDER_ORDER,
    )
    sections = [
        _section(
            'age',
            'Age',
            'bars',
            suppress_categories(_age_counts(served, end_date), order=AGE_ORDER),
        ),
        _section(
            'neighborhoods',
            'Neighborhood',
            'bars',
            suppress_categories(_neighborhood_counts(served), top_n=10),
        ),
        _zip_section(served),
        _section(
            'race',
            'Race and ethnicity',
            'bars',
            suppress_categories(
                _relabel(_grouped(served, 'demographic_info'), dict(Client.DEMOGRAPHIC_CHOICES), 'Unknown'),
                order=tuple(label for _key, label in Client.DEMOGRAPHIC_CHOICES) + ('Unknown',),
            ),
        ),
        _section(
            'gender',
            'Gender',
            'donut',
            gender_rows,
            donut_gradient=_donut_gradient(gender_rows),
        ),
        _section(
            'employment',
            'Work at sign-up',
            'bars',
            suppress_categories(
                _relabel(_grouped(served, 'employment_status'), dict(Client.EMPLOYMENT_STATUS_CHOICES), 'Unknown'),
                order=tuple(label for _key, label in Client.EMPLOYMENT_STATUS_CHOICES) + ('Unknown',),
            ),
        ),
        _section(
            'programs',
            'Program',
            'bars',
            suppress_categories(_program_counts(served)),
        ),
        _section(
            'months',
            'Started, by month',
            'columns',
            _month_rows(new, start_date, end_date) if new_count else [],
            empty_message='' if new_count else 'No one started in this period.',
        ),
    ]
    return sections


def _age_counts(served, as_of):
    """Age bins aggregated in the database. Boundaries match age_bin()."""
    known = served.exclude(dob__isnull=True).annotate(
        dob_month=ExtractMonth('dob'),
        dob_day=ExtractDay('dob'),
    ).annotate(
        age_years=_age_years_expression(as_of),
    ).annotate(
        age_label=Case(
            When(age_years__lt=0, then=Value('Unknown')),
            When(age_years__lt=18, then=Value('<18')),
            When(age_years__lte=24, then=Value('18-24')),
            When(age_years__lte=34, then=Value('25-34')),
            When(age_years__lte=44, then=Value('35-44')),
            When(age_years__lte=54, then=Value('45-54')),
            When(age_years__lte=64, then=Value('55-64')),
            default=Value('65+'),
            output_field=CharField(max_length=16),
        )
    )
    counts = {
        row['age_label']: row['count']
        for row in known.order_by().values('age_label').annotate(count=Count('pk'))
    }
    unknown = served.filter(dob__isnull=True).count()
    if unknown:
        counts['Unknown'] = counts.get('Unknown', 0) + unknown
    return counts


def _age_years_expression(as_of):
    birthday_not_yet = Case(
        When(
            Q(dob_month__gt=as_of.month) | Q(dob_month=as_of.month, dob_day__gt=as_of.day),
            then=Value(1),
        ),
        default=Value(0),
        output_field=IntegerField(),
    )
    return ExpressionWrapper(
        Value(as_of.year) - ExtractYear('dob') - birthday_not_yet,
        output_field=IntegerField(),
    )


def _program_counts(served):
    labels = dict(Client.TRAINING_INTEREST_CHOICES)
    raw = _grouped(served, 'training_interest')
    return {labels.get(key, key or 'Unknown'): count for key, count in raw.items()}


def _zip_section(served):
    bucketed = bucket_zips(_grouped(served, 'zip_code'))
    return _section(
        'zips',
        'ZIP codes',
        'bars',
        suppress_categories(bucketed, top_n=10),
        'ZIP codes outside San Francisco are combined. Blank ZIP codes are left out of this chart.',
        '' if bucketed else 'No ZIP codes on file.',
    )


def _neighborhood_counts(served):
    labels = dict(Client.NEIGHBORHOOD_CHOICES)
    raw = _grouped(served, 'neighborhood')
    return {labels.get(key, key or 'Unknown'): count for key, count in raw.items() if count}


def _grouped(qs, field):
    rows = qs.order_by().values(field).annotate(count=Count('pk'))
    grouped = {}
    for row in rows:
        key = row[field] if row[field] is not None else ''
        grouped[key] = grouped.get(key, 0) + row['count']
    return grouped


def _relabel(raw, mapping, default_label):
    labeled = {}
    for key, count in raw.items():
        label = mapping.get(key, default_label)
        labeled[label] = labeled.get(label, 0) + count
    return labeled


def _month_rows(new, start_date, end_date):
    raw = {}
    for row in new.annotate(month=TruncMonth('service_start')).order_by().values('month').annotate(count=Count('pk')):
        month = _as_month(row['month'])
        if month:
            raw[month] = raw.get(month, 0) + row['count']
    pairs = []
    for month in _iter_months(start_date, end_date):
        pairs.append((month.strftime('%b %Y'), raw.get(month, 0)))
    return series_rows(pairs)


def _section(section_id, title, layout, rows, detail='', empty_message='', donut_gradient=''):
    section = {
        'id': section_id,
        'title': title,
        'layout': layout,
        'rows': rows,
        'detail': detail,
        'empty_message': empty_message,
    }
    if donut_gradient:
        section['donut_gradient'] = donut_gradient
    return section


def _donut_gradient(rows):
    slices = []
    for row in rows:
        if row['suppressed'] or not row['percent_display']:
            continue
        slices.append(int(row['percent_display'].rstrip('%')))
    if not slices or sum(slices) <= 0:
        return ''
    stops = []
    cursor = 0
    for index, percent in enumerate(slices):
        end = cursor + percent
        color = DONUT_COLORS[index % len(DONUT_COLORS)]
        stops.append(f'{color} {cursor}% {end}%')
        cursor = end
    if cursor < 100:
        stops.append(f'{DONUT_COLORS[0]} {cursor}% 100%')
    return f"conic-gradient({', '.join(stops)})"


def _order_labels(counts, order):
    if not order:
        ranked = sorted(
            ((label, count) for label, count in counts.items() if label != OTHER_LABEL),
            key=lambda item: (-item[1], item[0]),
        )
        if OTHER_LABEL in counts:
            ranked.append((OTHER_LABEL, counts[OTHER_LABEL]))
        return ranked

    ordered = []
    seen = set()
    for label in order:
        if label in counts and label != OTHER_LABEL:
            ordered.append((label, counts[label]))
            seen.add(label)
    extras = sorted(
        ((label, count) for label, count in counts.items() if label not in seen and label != OTHER_LABEL),
        key=lambda item: (-item[1], item[0]),
    )
    ordered.extend(extras)
    if OTHER_LABEL in counts:
        ordered.append((OTHER_LABEL, counts[OTHER_LABEL]))
    return ordered


def _largest_remainder(counts, total):
    if total <= 0:
        return [0 for _count in counts]
    raw = [(count * 100) / total for count in counts]
    floors = [int(value) for value in raw]
    leftover = 100 - sum(floors)
    ranked = sorted(
        range(len(counts)),
        key=lambda index: (raw[index] - floors[index], counts[index]),
        reverse=True,
    )
    for index in ranked:
        if leftover <= 0:
            break
        if counts[index] <= 0:
            continue
        floors[index] += 1
        leftover -= 1
    return floors


def _format_change(current, prior):
    if prior <= 0:
        return None
    percent = round((current - prior) * 100 / prior)
    if percent > 0:
        return f'+{percent}%'
    if percent < 0:
        return f'{percent}%'
    return '0%'


def _share(part, whole):
    if not whole:
        return None
    return round((part or 0) * 100 / whole)


def _parse_date(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as exc:
        raise ReportPeriodError('Use dates in YYYY-MM-DD format.') from exc


def _last_completed_quarter(today):
    quarter_index = (today.month - 1) // 3
    if quarter_index == 0:
        return date(today.year - 1, 10, 1), date(today.year - 1, 12, 31)
    start_month = (quarter_index - 1) * 3 + 1
    end_month = start_month + 2
    return (
        date(today.year, start_month, 1),
        date(today.year, end_month, monthrange(today.year, end_month)[1]),
    )


def _add_years(day, years):
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)


def _iter_months(start_date, end_date):
    cursor = date(start_date.year, start_date.month, 1)
    last = date(end_date.year, end_date.month, 1)
    while cursor <= last:
        yield cursor
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)


def _as_month(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        value = value.date()
    if isinstance(value, date):
        return date(value.year, value.month, 1)
    if isinstance(value, str):
        parsed = datetime.strptime(value[:10], '%Y-%m-%d').date()
        return date(parsed.year, parsed.month, 1)
    return None


def _long_date(value):
    return f'{value.strftime("%B")} {value.day}, {value.year}'


def _timestamp_label(value):
    local = timezone.localtime(value)
    hour = int(local.strftime('%I'))
    return f'{_long_date(local.date())}, {hour}:{local.strftime("%M %p")} PT'
