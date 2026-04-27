# Manager Reports Quick Guide

This is the simplest way to pull reports and explain why they matter.

## Before you start

- Sign in to Django Admin first: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/`
- Keep that tab open.
- Open the Reports Hub in a new tab: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/`
- Set date range once, then click report buttons.
- Open CSV files in Excel or Google Sheets.

## Fast report links

Primary entry point:

- Reports Hub: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/`

Direct links (if needed):

- Available workers: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/available-workers/`
- Job placements: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/job-placements/`
- Call-outs: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/callouts/`
- Today's assignments: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/todays-assignments/`
- Client outcomes (program + demographics): `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/client-outcomes/`
- Staff follow-up scorecard: `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/staff-followup-scorecard/`
- Workforce inventory package (ZIP): `https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/workforce-inventory-package/`

## Most common manager use cases

### 1) Daily operations check (5 minutes)

Pull:

1. `todays-assignments`
2. `callouts`
3. `available-workers`

Why useful:

- Confirms who is staffed today.
- Shows who called out and where coverage is needed.
- Gives quick backup list for replacements.

### 2) Weekly case management check (15 minutes)

Pull:

1. `client-outcomes`
2. `staff-followup-scorecard`

Why useful:

- Shows caseload by case manager and program status.
- Highlights overdue follow-up pressure (30/60/90+).
- Makes it easy to coach staff and rebalance work.

### 3) Funder / OEWD style monthly reporting

Pull:

1. `client-outcomes`
2. `job-placements`
3. `callouts`

Why useful:

- Program participation and outcomes.
- Demographic and service mix.
- Staffing reliability and service delivery.

## Optional filters (copy/paste patterns)

You can add filters directly to the URL.

### Job placements

- Date range:
  - `.../api/reports/job-placements/?start_date=2026-04-01&end_date=2026-04-30`
- My records only:
  - `.../api/reports/job-placements/?mine=1`
- By logger name:
  - `.../api/reports/job-placements/?logged_by=Maria`

### Client outcomes

- My caseload only:
  - `.../api/reports/client-outcomes/?mine=1`
- By case manager:
  - `.../api/reports/client-outcomes/?case_manager=Maria`
- By program:
  - `.../api/reports/client-outcomes/?program=citybuild`
- By demographic:
  - `.../api/reports/client-outcomes/?demographic=latinx`
- By status:
  - `.../api/reports/client-outcomes/?status=active`
- By date range:
  - `.../api/reports/client-outcomes/?start_date=2025-04-20&end_date=2026-04-20`

### Staff follow-up scorecard

- Last 90 days (default):
  - `.../api/reports/staff-followup-scorecard/`
- Last 30 days:
  - `.../api/reports/staff-followup-scorecard/?since_days=30`
- My score only:
  - `.../api/reports/staff-followup-scorecard/?mine=1`

## What each report tells managers (plain English)

- `available-workers`: Who is likely ready for dispatch and recent reliability.
- `job-placements`: Who got placed, where, pay, work type, start date, and who logged the placement.
- `callouts`: Attendance risk and replacement pressure.
- `todays-assignments`: Live daily roster.
- `client-outcomes`: Caseload + progress + outcome tracking by manager/program/demographics.
- `staff-followup-scorecard`: Follow-up activity and overdue risk by staff member.

## Recommended manager routine

- Daily: `todays-assignments`, `callouts`, `available-workers`
- Weekly: `client-outcomes`, `staff-followup-scorecard`
- Monthly: export all from the Reports Hub with one date range and keep in a dated folder

## Troubleshooting

- If you get redirected or blocked, sign in to Admin first and try again.
- If a CSV looks blank, remove filters from the URL and retest.
- If a number looks wrong, verify date range and filter values first.

