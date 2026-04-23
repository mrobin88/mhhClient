# Pit Stop Notifications + Reporting Playbook

## Goal
Ensure every Pit Stop application is reviewed quickly and routed to the right team members.

## Who should be notified
- Executive Director (oversight)
- Program Manager (daily triage owner)
- Pit Stop Coordinator / Lead Case Manager (assignment owner)
- Optional backup mailbox (shared inbox for coverage)

Use `PITSTOP_APPLICATION_ALERT_EMAILS` in environment settings as a comma-separated list.

## Suggested notification targets
- Primary: program manager and Pit Stop lead
- Secondary: ED for visibility
- Optional: shared operations inbox for continuity

Example:

`PITSTOP_APPLICATION_ALERT_EMAILS=manager@missionhiringhall.org,pitstop@missionhiringhall.org,ed@missionhiringhall.org`

## Triage workflow (human process)
1. New application email arrives.
2. Program manager opens the admin link from the email.
3. Verify legal eligibility and contact details.
4. Check availability match against current shift needs.
5. Set outreach action (call/text/email) within 1 business day.
6. Add/update case note and assign next follow-up date.

## Report usage
Use the report endpoint to pull Pit Stop applications and isolate open-availability applicants:

- JSON list: `/api/pitstop-applications/report/`
- Open availability only: `/api/pitstop-applications/report/?open_availability=1`
- CSV export: `/api/pitstop-applications/report/?format=csv`
- CSV + open availability only: `/api/pitstop-applications/report/?format=csv&open_availability=1`

## Access control
- Public users can submit applications.
- Reporting endpoints are restricted to authenticated staff users.

