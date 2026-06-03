# Mission Hiring Hall — Staff How-To

This guide is for **frontline staff and managers**. It explains *why* we use this system and *how* to use it in real work — without technical jargon.

---

## Why we use this (the honest version)

| Without the system | With the system |
|--------------------|-----------------|
| Notes scattered in email, texts, and paper | One timeline per client |
| “Who has their ID?” is a guessing game | Document checklist on each profile |
| Funders ask for numbers — scramble to rebuild them | Reports export from the same data you enter |
| PitStop hours disputed | Clock in/out with time punches (location checked at site) |
| New staff inherit incomplete stories | Printable client file package for handoffs |

**The system only helps if we put enough in.** You do not need every field on day one. You *do* need:

- **Name + phone** when someone becomes a client  
- **A case note** when something meaningful happens (use **Note date** if it happened earlier)  
- **Documents** when you have them (upload when you get them — not “never”)  
- **PitStop workers** clocking in/out on the iPad portal when they work  

Supervisors use reports to coach and prepare for audits — not to catch people for missing optional fields.

---

## Bookmarks (save these)

| What | Link |
|------|------|
| **Staff Admin** (clients, notes, documents) | https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/admin/ |
| **Reports Hub** (downloads for managers) | https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net/api/reports/ |
| **Public registration** (client fills form on phone) | https://blue-glacier-0c5f06410.3.azurestaticapps.net/ |
| **Lobby check-in** (returning visitors) | https://blue-glacier-0c5f06410.3.azurestaticapps.net/checkin |
| **PitStop worker portal** (clock in/out) | https://blue-glacier-0c5f06410.3.azurestaticapps.net/worker/ |

**Reports tip:** Sign in to **Admin** first, then open **Reports Hub** in a new tab so downloads work.

---

## Daily work — case managers

### 1. Open or create a client

1. Go to **Admin → Clients**.  
2. Search by name or phone.  
3. To add someone new: **Add client**. Case manager (**staff name**) fills in automatically from your login.

### 2. Add a case note (one visit = one note)

**Best:** On the client page, use **+ Quick add note** or add a row under **Recent case notes**.

- **Note date** = when the interaction happened (use a past date for retroactive entry).  
- **System** column = when it was saved in the computer (automatic).  
- **Follow-up date** = when you need to act again (you may get email reminders).  
- Only the **most recent 40 notes** show on the profile; use **View all case notes** for older ones.

**Rule of thumb:** Do not paste a month of visits into one box. One row per visit.

### 3. Documents (when you have files)

On the client profile:

- **Document checklist** = quick ✓ / ○ (resume, ID, consent, intake, etc.).  
- **Open documents hub** = upload and download files.  
  Files are **not** loaded until you click download (keeps the page fast).

Upload when the client brings paperwork — empty checklist is normal until then.

### 4. Lobby check-in

Use **check-in** when someone is already in the system and visiting today. Staff can add a **Government Photo ID** at the kiosk when needed.

---

## PitStop workers (iPad / phone)

Workers use the **worker portal** — not the staff admin.

1. Staff creates a **worker account** for the client (admin list action).  
2. Worker logs in with **phone + PIN** (last 4 digits of phone unless changed).  
3. Worker **clocks in** and **clocks out** (optional map snapshot + cross-street label saved for reference — no geofence).  
4. Staff review hours under **Admin → Worker time punches** or **PitStop Hours** report.

**Staff workspace (new):** https://blue-glacier-0c5f06410.3.azurestaticapps.net/staff/ — same username/password as Admin; search clients and add quick case notes from a phone-friendly UI.

**We do not schedule shifts in this system anymore.** No assignment grid on the client page — only clock punches.

---

## Managers — reports (15-minute rhythm)

Open **Reports Hub**, then use **Manager package (recommended)** — a ZIP with `START_HERE.html`, full `client_outcomes.csv`, a printable summary, follow-up scorecard, and PitStop hours.

**Why exports looked small:** The hub used to limit outcomes to clients **created this month**. Leave **“Only clients created in activity date range”** unchecked to include your full caseload (300+).

| When | Download | Why |
|------|----------|-----|
| **Weekly** | Manager package ZIP | One click for managers |
| **Weekly** | Client Outcomes package | CSV + printable summary |
| **Before a meeting** | Client File Package | One client (lookup by ID/phone/name) |
| **Monthly / funder** | Workforce Inventory Package | Demographics rollups |

Activity dates still apply to **PitStop hours**. Check **Only my records** for your caseload only.

### Case manager auto-assignment

When a **non-admin** staff member **updates** a client in admin, **Case manager** is set to that person. **Admin-role** editors do not auto-reassign. Kiosk check-in does not change case manager.

---

## What good data looks like (minimum)

- **Every active client:** phone + at least one case note in the last 30 days (or a note explaining pause).  
- **Before program milestones:** checklist reviewed; upload ID/resume when you have them.  
- **PitStop:** workers clocked in/out on days they work — not “paper only.”  

Partial profiles are OK at intake. They are **not** OK forever with no notes and no docs.

---

## Common questions

**“The page was slow or errored.”**  
Tell your supervisor or tech contact. Superusers may see a detailed error page — copy the **Exception** line.

**“I don’t have documents yet.”**  
Save the client and notes anyway. Update the checklist when files arrive.

**“Why doesn’t staff use it?”**  
Usually: no time, no habit, or tools don’t match the floor. This guide + supervisor check-ins fix habit; missing docs fix timing.

**“Who maintains this?”**  
Internal tech — not something clients or most staff configure. Ask leadership before expecting new features.

---

## Quick troubleshooting

| Problem | Try |
|---------|-----|
| Report download blocked | Log into **Admin** first, then Reports Hub |
| Can’t find a client | Search phone without dashes; try last name only |
| Worker can’t clock in | Confirm worker account exists; correct site; location enabled on device |
| Note for a past date | Set **Note date** on the note row, not only today’s date |

---

*Last updated for: document hub, case note dates, PitStop time punches (no staff assignment scheduling).*
