"""Aggregate OEWD report: overlap, age bins, small cells, and one count per client."""
from datetime import date, datetime, time, timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.aggregate_report import (
    SMALL_CELL_THRESHOLD,
    age_bin,
    bucket_zips,
    date_range_for_preset,
    get_aggregate_report,
    previous_period,
    render_aggregate_csv,
    series_rows,
    suppress_categories,
)
from clients.models import CaseNote, Client, JobPlacement
from clients.models_classes import ClassEnrollment, ClassSession, ClassTemplate
from clients.models_extensions import WorkerAccount, WorkerDailyFeedback, WorkerTimePunch

WINDOW_START = date(2026, 7, 1)
WINDOW_END = date(2026, 9, 30)


def make_client(**kwargs):
    sequence = Client.objects.count() + 1
    defaults = {
        'first_name': 'ShouldNotLeak',
        'last_name': f'Person{sequence}',
        'phone': f'415555{sequence:04d}',
        'gender': 'F',
        'training_interest': 'general',
        'status': 'active',
        'program_start_date': date(2026, 8, 1),
        'demographic_info': 'asian',
        'employment_status': 'part_time',
        'neighborhood': 'mission',
        'zip_code': '94110',
        'dob': date(1990, 1, 15),
    }
    defaults.update(kwargs)
    return Client.objects.create(**defaults)


def kpis(report):
    return {item['key']: item for item in report['kpis']}


def section(report, section_id):
    return next(item for item in report['sections'] if item['id'] == section_id)


class DateRangeOverlapTests(TestCase):
    def test_overlap_new_enrollments_and_program_filter(self):
        make_client(program_start_date=date(2026, 1, 1))
        make_client(program_start_date=date(2026, 1, 1), program_completed_date=date(2026, 6, 30))
        make_client(program_start_date=date(2026, 1, 1), program_completed_date=WINDOW_START)
        make_client(program_start_date=WINDOW_END)
        make_client(program_start_date=date(2026, 10, 1))
        make_client(program_start_date=date(2026, 8, 15), training_interest='capsa')
        make_client(program_start_date=date(2026, 8, 15), training_interest='pit_stop')

        report = get_aggregate_report(WINDOW_START, WINDOW_END)
        summary = kpis(report)
        # Open from January, completed on the start date, started on the end date,
        # plus two August starts. The June exit and the October start are out.
        self.assertEqual(summary['unduplicated']['count'], 5)
        self.assertEqual(summary['new_enrollments']['count'], 3)
        self.assertEqual(summary['programs']['count'], 3)
        self.assertEqual(report['exits_recorded'], 1)

        capsa = get_aggregate_report(WINDOW_START, WINDOW_END, 'capsa')
        self.assertEqual(kpis(capsa)['unduplicated']['count'], 1)
        self.assertEqual(kpis(capsa)['new_enrollments']['count'], 1)
        self.assertEqual(capsa['program_label'], 'CAPSA')

    def test_sign_up_timestamp_uses_los_angeles_date(self):
        # 2026-07-01 06:30 UTC is still June 30 in Pacific time.
        client = make_client(program_start_date=None)
        client.created_at = datetime(2026, 7, 1, 6, 30, tzinfo=datetime_timezone.utc)
        client.save(update_fields=['created_at'])

        july = get_aggregate_report(date(2026, 7, 1), date(2026, 7, 31))
        june = get_aggregate_report(date(2026, 6, 30), date(2026, 6, 30))
        # Sign-up is June 30 in Pacific time, so it is not a July enrollment.
        # It still counts as served in July because there is no completion date.
        self.assertEqual(kpis(july)['new_enrollments']['count'], 0)
        self.assertEqual(kpis(july)['unduplicated']['count'], 1)
        self.assertEqual(kpis(june)['new_enrollments']['count'], 1)
        self.assertEqual(kpis(june)['unduplicated']['count'], 1)

    def test_prior_period_is_the_equal_length_window_before_start(self):
        self.assertEqual(previous_period(date(2026, 8, 1), date(2026, 8, 31)), (date(2026, 7, 1), date(2026, 7, 31)))
        make_client(program_start_date=date(2026, 7, 15))
        make_client(program_start_date=date(2026, 8, 15))
        make_client(program_start_date=date(2026, 8, 16))

        report = get_aggregate_report(date(2026, 8, 1), date(2026, 8, 31))
        summary = kpis(report)
        self.assertEqual(summary['new_enrollments']['count'], 2)
        self.assertEqual(summary['new_enrollments']['prior'], 1)
        self.assertEqual(summary['new_enrollments']['change_display'], '+100%')
        # July starter has no completion date, so August still counts them.
        self.assertEqual(summary['unduplicated']['count'], 3)
        self.assertEqual(summary['unduplicated']['change_display'], '+200%')


class AgeBinTests(TestCase):
    def test_boundaries_as_of_range_end(self):
        as_of = date(2026, 6, 30)
        cases = {
            date(2008, 7, 1): '<18',
            date(2008, 6, 30): '18-24',
            date(2002, 6, 30): '18-24',
            date(2001, 6, 30): '25-34',
            date(1992, 6, 30): '25-34',
            date(1991, 6, 30): '35-44',
            date(1982, 6, 30): '35-44',
            date(1981, 6, 30): '45-54',
            date(1972, 6, 30): '45-54',
            date(1971, 6, 30): '55-64',
            date(1962, 6, 30): '55-64',
            date(1961, 6, 30): '65+',
            None: 'Unknown',
        }
        for dob, label in cases.items():
            self.assertEqual(age_bin(dob, as_of), label, dob)

    def test_database_bins_match_age_bin(self):
        as_of = date(2026, 6, 30)
        births = [
            date(2008, 7, 1),
            date(2008, 6, 30),
            date(2001, 6, 30),
            date(1991, 6, 30),
            date(1981, 6, 30),
            date(1971, 6, 30),
            date(1961, 6, 30),
            None,
        ]
        for index, dob in enumerate(births):
            make_client(
                dob=dob,
                program_start_date=date(2026, 6, 1),
                gender='F' if index % 2 == 0 else 'M',
            )
        # Five more 25-year-olds so that bin survives suppression and can be read back.
        for _index in range(4):
            make_client(dob=date(2001, 6, 30), program_start_date=date(2026, 6, 1))

        report = get_aggregate_report(date(2026, 6, 1), as_of)
        age_rows = {row['label']: row['count_display'] for row in section(report, 'age')['rows']}
        self.assertEqual(age_rows['25-34'], '5')
        self.assertNotIn('<18', age_rows)
        self.assertIn('Other', age_rows)

        from clients.aggregate_report import _age_counts, _cohorts

        served, _new = _cohorts(date(2026, 6, 1), as_of, None)
        counted = _age_counts(served, as_of)
        expected = {}
        for dob in births + [date(2001, 6, 30)] * 4:
            label = age_bin(dob, as_of)
            expected[label] = expected.get(label, 0) + 1
        self.assertEqual(counted, expected)


class SmallCellSuppressionTests(TestCase):
    def test_groups_under_five_roll_into_other_and_leave_percents(self):
        self.assertEqual(SMALL_CELL_THRESHOLD, 5)
        rows = suppress_categories({'Female': 6, 'Male': 3, 'Non-binary': 1})
        self.assertEqual([(row['label'], row['count_display'], row['percent_display']) for row in rows], [
            ('Female', '6', '100%'),
            ('Other', '<5', ''),
        ])
        self.assertNotIn('3', [row['count_display'] for row in rows])
        self.assertNotIn('1', [row['count_display'] for row in rows])

    def test_combined_other_is_shown_once_it_reaches_five(self):
        rows = suppress_categories({'Female': 6, 'Male': 3, 'Non-binary': 3})
        displayed = {row['label']: row for row in rows}
        self.assertEqual(displayed['Female']['percent_display'], '50%')
        self.assertEqual(displayed['Other']['count_display'], '6')
        self.assertEqual(displayed['Other']['percent_display'], '50%')

    def test_top_10_remainder_joins_other_before_suppression(self):
        counts = {f'{94102 + index}': 10 for index in range(12)}
        rows = suppress_categories(counts, top_n=10)
        other = next(row for row in rows if row['label'] == 'Other')
        self.assertEqual(other['count_display'], '20')
        self.assertEqual(len(rows), 11)

    def test_months_stay_in_place(self):
        rows = series_rows([('Jul 2026', 6), ('Aug 2026', 2), ('Sep 2026', 0)])
        self.assertEqual(rows[1]['label'], 'Aug 2026')
        self.assertEqual(rows[1]['count_display'], '<5')
        self.assertEqual(rows[1]['percent_display'], '')
        self.assertEqual(rows[0]['percent_display'], '100%')
        self.assertEqual(rows[2]['count_display'], '0')

    def test_report_gender_does_not_publish_the_small_count(self):
        for _index in range(6):
            make_client(gender='F', program_start_date=date(2026, 8, 1))
        for _index in range(3):
            make_client(gender='M', program_start_date=date(2026, 8, 1))
        report = get_aggregate_report(date(2026, 8, 1), date(2026, 8, 31))
        gender = section(report, 'gender')['rows']
        self.assertEqual([row['label'] for row in gender], ['Female', 'Other'])
        self.assertEqual(gender[0]['count_display'], '6')
        self.assertEqual(gender[1]['count_display'], '<5')
        blob = render_aggregate_csv(report)
        self.assertNotIn('Gender,Male,3', blob.replace(' ', ''))
        self.assertNotIn('ShouldNotLeak', blob)


class DistinctClientTests(TestCase):
    def test_one_client_is_counted_once_across_notes_and_attendance(self):
        client = make_client(program_start_date=date(2026, 1, 1), phone='4155557777')
        make_client(program_start_date=date(2026, 1, 1), phone='4155557777', gender='M')
        for day in range(1, 6):
            CaseNote.objects.create(
                client=client,
                staff_member='Staff',
                content='Visit',
                note_date=date(2026, 9, day),
            )
        template = ClassTemplate.objects.create(
            name='Orientation',
            start_time=time(9, 0),
            end_time=time(12, 0),
            program='general',
        )
        first = ClassSession.objects.create(
            template=template,
            session_date=date(2026, 8, 1),
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        second = ClassSession.objects.create(
            template=template,
            session_date=date(2026, 8, 8),
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        ClassEnrollment.objects.create(session=first, client=client, status='attended')
        ClassEnrollment.objects.create(session=second, client=client, status='attended')

        report = get_aggregate_report(WINDOW_START, WINDOW_END)
        summary = kpis(report)
        self.assertEqual(summary['unduplicated']['count'], 2)
        self.assertEqual(summary['recently_active']['count'], 1)
        gender_counts = [row['count_display'] for row in section(report, 'gender')['rows']]
        self.assertNotIn('5', gender_counts)

    def test_recent_activity_sources_and_window(self):
        noted = make_client(program_start_date=date(2026, 1, 1))
        CaseNote.objects.create(
            client=noted,
            staff_member='Staff',
            content='Too early',
            note_date=date(2026, 7, 1),
        )
        in_window = make_client(program_start_date=date(2026, 1, 1))
        CaseNote.objects.create(
            client=in_window,
            staff_member='Staff',
            content='In window',
            note_date=date(2026, 7, 2),
        )
        attended = make_client(program_start_date=date(2026, 1, 1))
        registered = make_client(program_start_date=date(2026, 1, 1))
        template = ClassTemplate.objects.create(
            name='Workshop',
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        session = ClassSession.objects.create(
            template=template,
            session_date=date(2026, 8, 1),
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        ClassEnrollment.objects.create(session=session, client=attended, status='attended')
        ClassEnrollment.objects.create(session=session, client=registered, status='registered')

        punched = make_client(program_start_date=date(2026, 1, 1), phone='4155558100')
        account = WorkerAccount.objects.create(client=punched, phone='4155558100', pin_hash='test')
        WorkerTimePunch.objects.create(
            worker_account=account,
            clock_in_at=datetime(2026, 8, 1, 19, 0, tzinfo=datetime_timezone.utc),
        )
        feedback_client = make_client(program_start_date=date(2026, 1, 1), phone='4155558101')
        feedback_account = WorkerAccount.objects.create(
            client=feedback_client,
            phone='4155558101',
            pin_hash='test',
        )
        WorkerDailyFeedback.objects.create(
            worker_account=feedback_account,
            feedback_date=date(2026, 8, 2),
            feedback_text='Shift went fine',
        )

        report = get_aggregate_report(WINDOW_START, WINDOW_END)
        # July 1 is 91 days before September 30, so that note is outside the window.
        self.assertEqual(kpis(report)['recently_active']['count'], 4)
        self.assertEqual(kpis(report)['unduplicated']['count'], 6)

    def test_job_placement_counts_a_client_once(self):
        client = make_client(program_start_date=date(2026, 1, 1), job_placement_date=date(2026, 8, 4))
        JobPlacement.objects.create(
            client=client,
            employer='SecretEmployer',
            work_type='full_time',
            start_date=date(2026, 8, 4),
        )
        other = make_client(program_start_date=date(2026, 1, 1))
        other.job_placement_date = date(2026, 8, 20)
        other.save(update_fields=['job_placement_date'])

        report = get_aggregate_report(WINDOW_START, WINDOW_END)
        self.assertEqual(report['job_placements'], 2)
        self.assertNotIn('SecretEmployer', render_aggregate_csv(report))


class CompletenessAndZipTests(TestCase):
    def test_completeness_uses_served_clients(self):
        stamp = datetime(2026, 8, 15, 19, 0, tzinfo=datetime_timezone.utc)
        rows = [
            {'zip_code': '', 'dob': date(1990, 1, 1), 'gender': 'F'},
            {'zip_code': '94110', 'dob': None, 'gender': 'F'},
            {'zip_code': '94103', 'dob': None, 'gender': ''},
            {'zip_code': '   ', 'dob': date(1980, 5, 1), 'gender': 'M', 'program_completed_date': date(2026, 8, 20)},
        ]
        for fields in rows:
            client = make_client(program_start_date=None, **fields)
            client.created_at = stamp
            client.save(update_fields=['created_at'])

        report = get_aggregate_report(date(2026, 8, 1), date(2026, 8, 31))
        completeness = report['completeness']
        self.assertEqual(completeness['served'], 4)
        self.assertEqual(completeness['no_exit_pct'], 75)
        self.assertEqual(completeness['missing_zip_pct'], 50)
        self.assertEqual(completeness['missing_dob_pct'], 50)
        self.assertEqual(completeness['missing_gender_pct'], 25)
        self.assertEqual(completeness['missing_program_start_pct'], 100)
        self.assertEqual(report['exits_recorded'], 1)
        self.assertIn('75% have no end date on file', completeness['text'])
        self.assertIn('50% are missing a birth date', completeness['text'])

    def test_zip_buckets_and_outside_san_francisco(self):
        self.assertEqual(
            bucket_zips({'94110': 6, '94110-1234': 1, '94601': 4, '': 3, 'ab': 2}),
            {'94110': 7, 'Outside San Francisco': 4},
        )


class PresetTests(TestCase):
    def test_fiscal_year_and_last_quarter(self):
        self.assertEqual(date_range_for_preset('fiscal_ytd', date(2026, 10, 5)), (date(2026, 7, 1), date(2026, 10, 5)))
        self.assertEqual(date_range_for_preset('fiscal_ytd', date(2026, 3, 1)), (date(2025, 7, 1), date(2026, 3, 1)))
        self.assertEqual(date_range_for_preset('last_quarter', date(2026, 10, 5)), (date(2026, 7, 1), date(2026, 9, 30)))
        self.assertEqual(date_range_for_preset('last_quarter', date(2026, 2, 1)), (date(2025, 10, 1), date(2025, 12, 31)))
        self.assertEqual(date_range_for_preset('calendar_year', date(2026, 10, 5)), (date(2026, 1, 1), date(2026, 10, 5)))
        self.assertEqual(date_range_for_preset('last_12', date(2026, 10, 5)), (date(2025, 10, 6), date(2026, 10, 5)))


class ImpactReportPageTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser(
            username='impact-report',
            password='testpass123',
            email='impact@example.com',
        )
        self.http = DjangoClient()
        self.http.force_login(user)
        self.client_row = make_client(
            first_name='ShouldNotLeak',
            phone='4155550199',
            program_start_date=date(2020, 1, 1),
        )

    def test_page_is_aggregate_and_drops_client_report_links(self):
        response = self.http.get(reverse('reports-hub'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('Program Impact Report', body)
        self.assertIn('Prepared for SF OEWD', body)
        self.assertIn('Mission Hiring Hall', body)
        self.assertIn('People served', body)
        self.assertIn('Export PDF', body)
        self.assertIn('Export CSV', body)
        self.assertNotIn('ShouldNotLeak', body)
        self.assertNotIn('4155550199', body)
        self.assertNotIn('client-outcomes', body)
        self.assertNotIn('client-file-package', body)
        self.assertNotIn('Client File Package', body)

    def test_csv_has_totals_only(self):
        response = self.http.get(reverse('impact-report-csv'), {'preset': 'calendar_year'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        body = response.content.decode()
        self.assertIn('People served', body)
        self.assertNotIn('ShouldNotLeak', body)
        self.assertNotIn('4155550199', body)
        self.assertNotIn('Client ID', body)

    def test_anonymous_users_are_sent_to_login(self):
        response = DjangoClient().get(reverse('reports-hub'))
        self.assertEqual(response.status_code, 302)

    def test_bad_custom_range_does_not_build_a_report(self):
        response = self.http.get(reverse('reports-hub'), {
            'preset': 'custom',
            'start_date': '2026-08-01',
            'end_date': '2026-07-01',
        })
        self.assertContains(response, 'start date has to be on or before the end date')
        csv_response = self.http.get(reverse('impact-report-csv'), {
            'preset': 'custom',
            'start_date': 'nope',
            'end_date': '2026-07-01',
        })
        self.assertEqual(csv_response.status_code, 400)

    def test_client_level_export_still_exists(self):
        response = self.http.get(reverse('client-file-package'), {'client_lookup': str(self.client_row.pk)})
        self.assertEqual(response.status_code, 200)
