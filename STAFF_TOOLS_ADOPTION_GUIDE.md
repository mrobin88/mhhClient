# Staff Tools Adoption Guide (Non-Technical)

This guide is written for frontline staff and managers who want faster workflows, better reporting, and cleaner client files without extra manual work.

## Why staff should use these tools

- Save time: less copy/paste and fewer manual report edits.
- Improve quality: case notes and timelines stay consistent.
- Reduce stress during audits: printable files are ready when needed.
- Improve teamwork: everyone sees the same current client story.
- Increase trust in data: reports come from one system, not separate spreadsheets.

## What changed

### 1) Reports Hub now has better selectors

At `/api/reports/`, staff can now set filters once and download reports with those filters applied:

- Date range
- Program
- Client status
- Work type
- Follow-up window
- Case manager / logger name
- "Only my records"
- Client lookup (ID, phone, or name) for client file packages

This helps staff avoid editing URLs manually and reduces mistakes in exports.

### 2) New Client File Package (Printable)

New report endpoint: `/api/reports/client-file-package/`

For one client, staff can download a ZIP with:

- `client_profile.csv` (basic client details)
- `case_notes_timeline.csv` (chronological case notes)
- `printable_client_profile.html` (ready to print/share internally)

The printable includes:

- Client info
- Program timeline
- Plain-language narrative summary
- Case notes timeline with next steps and follow-up dates

This is designed to replace "fudged" manual case-note summaries with a reliable, reusable printable.

### 3) PitStop `/worker` login looks cleaner

The worker login screen has a clearer visual design and a direct "why this helps" message so workers understand the value quickly.

## Simple staff workflow to start using this

### Daily (operations)

1. Open Reports Hub: `/api/reports/`
2. Set date range + "Only my records" if needed
3. Download:
   - Today's Assignments
   - Call-outs
   - Available workers

### Weekly (case management)

1. Open Reports Hub and set your filters.
2. Download:
   - Client Outcomes
   - Staff Follow-up Scorecard
3. For specific client meetings, use the Client File Package and print `printable_client_profile.html`.

### Monthly (funder/audit prep)

1. Download Workforce Inventory Package.
2. For flagged/high-priority clients, also save Client File Packages.
3. Store all files in a monthly folder for easy retrieval.

## Where to host this documentation

You have three good options. Start simple:

### Option A (recommended): Keep it on your current URL

Host this guide on the same frontend domain as a help page (for example `/help/staff-tools`).

Why this is best:

- No new platform to manage
- Staff already trust that URL
- Easy to link from existing pages and onboarding docs

### Option B: Keep Markdown in your GitHub repo

Pros:

- Fast to publish
- Version history included

Cons:

- Less friendly for non-technical staff
- Harder to discover unless linked clearly

### Option C: Internal wiki (Notion/Confluence/SharePoint)

Pros:

- Familiar for operations teams
- Easy to edit by non-developers

Cons:

- Can drift out of sync with the real app if not maintained

## Recommended rollout plan (2 weeks)

### Week 1

- Share this guide with all staff.
- During team meeting, demo:
  - selectors in Reports Hub
  - Client File Package printable
- Ask each case manager to use one printable in a real client meeting.

### Week 2

- Collect feedback:
  - Which selectors are still confusing?
  - Is printable narrative useful as-is?
  - What is still manual?
- Make one update cycle based on real usage.

## Success metrics to track

- % of weekly staff using Reports Hub
- # of Client File Packages generated per week
- Reduction in manually drafted case-note summaries
- Faster prep time for manager/funder reporting

## Quick troubleshooting

- If reports fail to open: sign in to admin first, then reopen `/api/reports/`.
- If Client File Package says no match: use client ID or full phone digits.
- If data looks wrong: verify date range and filters before escalating.

