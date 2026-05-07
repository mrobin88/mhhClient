# Worker Portal Technical Guide

## Purpose and System Boundary

The Worker Portal exists to solve a specific operational problem: PitStop watch coverage has to be filled quickly by field workers who are not backend operators. The portal is therefore intentionally narrow.

This application is **not** a staff admin surface and is **not** a replacement for Django Admin.

- **Primary users of `/worker`**: PitStop coverage workers using phone + PIN.
- **Primary users of backend/admin**: a small staff cohort responsible for posting shifts and making selection decisions.
- **Design constraint**: workers should be able to complete their entire portal workflow without any dependency on admin knowledge, admin URLs, or staff-only tooling.

If a requirement cannot be justified inside that worker workflow, it should not be added to the worker surface.

---

## Product Model

The current Worker Portal is a coverage signaling system, not a full workforce management suite.

### In scope

- Worker authentication (phone + PIN)
- Read open PitStop coverage posts
- Submit interest for a posted open shift
- Track outcome of submitted interest

### Out of scope

- Worker self-scheduling
- Assignment editing
- Payroll/timekeeping
- Access to staff-only operational controls
- Any requirement to access Django Admin

---

## Runtime Architecture

### Frontend

- Vue 3 + TypeScript app mounted at `/worker`
- Core container: `frontend/src/worker/WorkerApp.vue`
- Primary views:
  - `WorkerLogin.vue`
  - `WorkerOpenShifts.vue`
  - `WorkerMyRequests.vue`

### Backend

- Django REST endpoints under `/api/worker/*`
- Token-backed worker sessions stored in database table `WorkerSessionToken`
- Resource models:
  - `WorkerAccount`
  - `OpenShift`
  - `ShiftCoverInterest`

### Authentication split

- Worker endpoints (`/api/worker/*`) use worker token semantics.
- Staff status updates for worker interests (`/api/staff/shift-interests/:id/`) use Django staff auth.

This split is deliberate and should remain explicit to prevent privilege drift.

---

## Access Control Model

The platform uses two separate trust domains:

1. **Worker domain**
   - Credential type: phone + PIN
   - Session artifact: worker token
   - Privileges: read open shifts, create/read own interest rows

2. **Staff domain**
   - Credential type: Django session (staff user)
   - Privileges: update interest status, post/manage staffing data in staff interfaces

Any endpoint mixing both credential models in the same action path should be treated as a security smell and refactored.

---

## UX Contract for Workers

The worker UX is now intentionally framed around coverage:

- Header and navigation language use **coverage board** semantics rather than generic admin terms.
- Open-shift copy clarifies that workers are signaling availability, not self-assigning.
- Response history view clarifies that status changes are staff-driven and visible asynchronously.

This wording matters. Precision in labels reduces operational misunderstanding and decreases staff correction overhead.

---

## API Surface

### Worker endpoints

- `POST /api/worker/login/`
- `POST /api/worker/logout/`
- `GET /api/worker/profile/`
- `GET /api/worker/open-shifts/`
- `GET|POST /api/worker/shift-interests/`

### Staff endpoint operating on worker records

- `PATCH /api/staff/shift-interests/:id/`

The staff endpoint is not intended for worker clients and should not be surfaced in worker UI.

---

## Data and Status Semantics

### `OpenShift`

Represents staff-published coverage demand for a specific site/date/time window.

### `ShiftCoverInterest`

Represents a worker declaration of availability for an open shift, with lifecycle states:

- `pending`
- `selected`
- `not_selected`
- `cancelled`

Interpretation: this record is a staffing intent workflow artifact, not a legal schedule assignment.

---

## Operational Workflow

### Worker-side workflow

1. Authenticate in portal.
2. Review currently open coverage posts.
3. Submit interest for one or more posts.
4. Return later to review status transitions.

### Staff-side workflow

1. Publish and maintain open coverage posts.
2. Review worker interest queue.
3. Mark responses as selected / not selected / cancelled.
4. Communicate final staffing outcomes through normal operations channels.

The worker portal purposely does not encode the entire staff communication process; it only tracks response state.

---

## Why Workers Must Not Depend on Admin

Operationally, requiring workers to navigate admin creates:

- Unnecessary cognitive load for frontline users
- Security and permission leakage risk
- Training burden disconnected from task reality
- Fragile workflows when staff-only screens change

Architecturally, this violates bounded-context design. Worker clients should consume worker endpoints only.

---

## Documentation Positioning

This guide is technical and architecture-first. It is intended for maintainers, implementers, and operations leadership evaluating scope and correctness.

For staff onboarding and adoption messaging, use:

- `STAFF_TOOLS_ADOPTION_GUIDE.md`
- `MANAGER_REPORTS_QUICK_GUIDE.md`
- `CASE_NOTES_GUIDE.md`

Keep this file focused on system boundary, data semantics, and implementation constraints.

---

## Current Implementation Notes

Recent portal updates aligned the UI language and interaction model with the intended domain:

- `WorkerApp.vue`
  - Retitled primary surface to "PitStop Coverage Board"
  - Renamed tabs to "Coverage needed" and "My responses"
- `WorkerOpenShifts.vue`
  - Clarified coverage-post semantics and staff confirmation requirement
  - Updated empty state language
- `WorkerMyRequests.vue`
  - Clarified that this list is response/status history
  - Updated empty state language for coverage context

These are not cosmetic-only edits; they reduce domain ambiguity and reinforce role boundaries.

---

## Extension Rules

When extending Worker Portal capabilities, enforce all rules below:

1. A worker must never require admin access to complete a worker task.
2. Worker endpoints should only return worker-relevant, least-privilege data.
3. Any staff mutation path should remain in staff-authenticated endpoints.
4. UI labels must encode actual business semantics (availability signal vs assignment confirmation).
5. New features should be validated against the original purpose: filling PitStop coverage with minimal friction.

If a proposed enhancement fails these tests, it belongs in staff tooling, not Worker Portal.

---

## Summary

Worker Portal is a constrained, purpose-built frontline surface for PitStop coverage operations. The backend/admin remains a staff-only operational system. Maintaining this separation is central to usability, security, and long-term maintainability.

# 🏢 Worker Portal System Guide

## Overview

The **Worker Portal** is a mobile-first web application that allows PitStop workers to:
- View their work assignments
- Update their availability
- Submit call-outs when unable to work
- Report facility issues and service requests
- Manage their schedule

This system complements the existing Client Services Management System by providing direct worker access to essential workforce management features.

---

## 🎯 Key Features

### 1. **Worker Authentication**
- Simple phone number + PIN login
- No complex passwords to remember
- Account lockout after failed attempts (security)
- Session-based authentication

### 2. **Dashboard**
- Today's assignments at a glance
- Upcoming shifts (next 7 days)
- Monthly statistics
- Recent service requests

### 3. **My Assignments**
- View all assignments (today, upcoming, past)
- Confirm assignments
- Submit call-outs with reason
- Contact supervisor directly
- Filter by status

### 4. **Availability Management**
- Set weekly availability schedule
- Choose preferred time slots
- Add notes for specific restrictions
- Easy toggle for each day of the week

### 5. **Service Requests**
- Report facility issues
- Upload photos of problems
- Set priority level
- Track request status
- View resolution notes

---

## 🔧 Technical Architecture

### Backend (Django)

**New Models:**
```
WorkerAccount
├─ client (ForeignKey to Client)
├─ phone (unique login identifier)
├─ pin_hash (hashed PIN)
├─ is_active, is_approved
├─ last_login, login_attempts
└─ locked_until (account lockout)

ServiceRequest
├─ submitted_by (ForeignKey to Client)
├─ work_site (ForeignKey to WorkSite)
├─ issue_type, title, description
├─ priority, status
├─ photo (optional)
├─ acknowledged_by, resolved_at
└─ resolution_notes
```

**API Endpoints:**
```
POST   /api/worker/login/                    - Worker login
POST   /api/worker/logout/                   - Worker logout
GET    /api/worker/profile/                  - Get worker profile
GET    /api/worker/dashboard/                - Dashboard summary
GET    /api/worker/assignments/              - List assignments
POST   /api/worker/assignments/:id/confirm/  - Confirm assignment
POST   /api/worker/call-out/                 - Submit call-out
GET    /api/worker/availability/             - Get availability
PUT    /api/worker/availability/             - Update availability
GET    /api/worker/service-requests/         - List service requests
POST   /api/worker/service-requests/         - Submit new request
GET    /api/worker/work-sites/               - List active work sites
```

### Frontend (Vue.js + TypeScript)

**Structure:**
```
frontend/src/worker/
├─ WorkerApp.vue                    - Main app container
├─ main.ts                          - Entry point
└─ components/
   ├─ WorkerLogin.vue               - Login page
   ├─ WorkerDashboard.vue           - Dashboard view
   ├─ WorkerAssignments.vue         - Assignments list + call-out
   ├─ WorkerAvailability.vue        - Availability editor
   └─ WorkerServiceRequests.vue     - Service request form + list
```

**Styling:**
- Tailwind CSS (mobile-first)
- Responsive design (works on all devices)
- Bottom navigation on mobile
- Sidebar navigation on desktop

---

## 👥 User Workflows

### Worker Daily Workflow

1. **Morning Check:**
   - Login with phone + PIN
   - View today's assignments on dashboard
   - Confirm assignments if needed
   - Check work site details and supervisor contact

2. **During Shift:**
   - Report issues using service request form
   - Upload photos of problems
   - Set priority (urgent, high, medium, low)

3. **Emergencies:**
   - Submit call-out if unable to work
   - Provide advance notice (hours)
   - Explain reason
   - System notifies staff immediately

4. **Weekly Planning:**
   - Update availability for upcoming week
   - Set preferred time slots
   - Add notes for restrictions

### Staff Admin Workflow

1. **Worker Account Management:**
   - Create worker accounts in Django Admin
   - Approve new accounts
   - Reset PINs if forgotten (default: last 4 digits of phone)
   - Deactivate/unlock accounts

2. **Service Request Management:**
   - View all submitted requests
   - Acknowledge requests
   - Assign to maintenance staff
   - Mark as resolved with notes
   - Track response/resolution times

3. **Monitoring:**
   - View worker login activity
   - Track service request trends
   - Monitor call-out patterns
   - Export reports

---

## 🚀 Setup Instructions

### 1. Backend Setup (Already Complete)

The following have been implemented:
- ✅ Models (WorkerAccount, ServiceRequest)
- ✅ Migrations applied
- ✅ Admin interfaces registered
- ✅ API endpoints created
- ✅ URL routes configured

### 2. Frontend Development

**To run the worker portal locally:**

```bash
cd frontend
npm install
npm run dev -- --host
```

Access at: http://localhost:5173/worker.html

**To build for production:**

```bash
npm run build
```

This creates optimized files in `frontend/dist/`.

### 3. Create Your First Worker Account

**Via Django Admin:**

1. Login to Django Admin: `/admin/`
2. Go to "Worker Accounts"
3. Click "Add Worker Account"
4. Select a client (must have Client record first)
5. Enter phone number
6. PIN will be set to last 4 digits of phone automatically
7. Check "Is Active" and "Is Approved"
8. Save

**Via Django Shell:**

```python
python manage.py shell

from clients.models import Client
from clients.models_extensions import WorkerAccount

# Get or create a client
client = Client.objects.get(phone='415-555-1234')

# Create worker account
account = WorkerAccount.objects.create(
    client=client,
    phone=client.phone,
    is_active=True,
    is_approved=True,
    created_by='Admin'
)
account.set_pin('1234')  # Set a PIN
account.save()
```

### 4. Testing the Worker Portal

1. Navigate to worker portal: `/worker.html`
2. Login with:
   - Phone: (worker's phone number)
   - PIN: (default is last 4 digits of phone, or custom PIN)
3. Test features:
   - View dashboard
   - Check assignments
   - Update availability
   - Submit service request

---

## 🔒 Security Features

### Authentication
- PIN hashing (Django's built-in password hasher)
- Session tokens (UUID-based)
- Account lockout after 5 failed attempts (30-minute lockout)
- Active/approved status checks

### Authorization
- Workers can only access their own data
- Token verification on all API endpoints
- Staff-only access to admin interface

### Best Practices
- PINs should be 4-6 digits
- Change default PIN on first login (recommended)
- Regular account audits
- Monitor failed login attempts

---

## 📊 Admin Features

### Worker Account Admin

**Actions:**
- Approve selected accounts
- Deactivate selected accounts
- Reset PIN to phone last 4 digits
- Unlock locked accounts

**Filters:**
- Is Active
- Is Approved
- Created Date

**Search:**
- Worker name
- Phone number

### Service Request Admin

**Actions:**
- Acknowledge requests
- Mark as In Progress
- Mark as Resolved

**Filters:**
- Status
- Priority
- Issue Type
- Work Site
- Created Date

**Metrics:**
- Response time (time to acknowledgement)
- Resolution time (time to resolution)
- Overdue status (based on priority)

---

## 🎨 Customization

### Adding New Issue Types

Edit `clients/models_extensions.py`:

```python
ISSUE_TYPE_CHOICES = [
    ('bathroom', 'Bathroom Issue'),
    ('supplies', 'Supplies Needed'),
    ('safety', 'Safety Concern'),
    ('equipment', 'Equipment Problem'),
    ('cleaning', 'Cleaning Issue'),
    ('vandalism', 'Vandalism'),  # NEW
    ('other', 'Other')
]
```

Run migration:
```bash
python manage.py makemigrations
python manage.py migrate
```

Update frontend `WorkerServiceRequests.vue` to include new option.

### Customizing Time Slots

Edit `clients/models_extensions.py`:

```python
TIME_SLOT_CHOICES = [
    ('6-12', '6am-12pm'),
    ('13-21', '1pm-9pm'),
    ('22-5', '10pm-5am'),
    ('custom', 'Custom'),  # NEW
]
```

Update frontend `WorkerAvailability.vue` timeSlots array.

---

## 📱 Mobile Optimization

The worker portal is designed mobile-first:

- **Responsive Layout:** Works on phones, tablets, desktops
- **Touch-Friendly:** Large buttons and touch targets
- **Bottom Navigation:** Easy one-handed use on mobile
- **Fast Loading:** Optimized bundle size
- **Offline-Ready:** Can be made into PWA (future enhancement)

---

## 🔄 Integration with Existing System

The worker portal integrates seamlessly with your existing Client Services system:

- **Shared Database:** Workers are linked to Client records
- **Same Azure Infrastructure:** Deployed in same resource group
- **Unified Admin:** Staff manage everything from Django Admin
- **API Consistency:** Uses same serialization patterns
- **No Data Duplication:** WorkAssignment model shared

---

## 📈 Future Enhancements

Potential improvements:

1. **SMS Notifications:**
   - New assignment notifications
   - Call-out confirmations
   - Service request updates
   - Use Twilio or similar service

2. **Push Notifications:**
   - Convert to Progressive Web App (PWA)
   - Real-time shift updates

3. **Geolocation:**
   - Clock in/out at work site
   - Verify worker is on-site

4. **Payroll Integration:**
   - Track hours worked
   - Export to payroll system

5. **Multi-language Support:**
   - Spanish translation
   - Chinese translation

6. **Advanced Analytics:**
   - Worker performance metrics
   - Reliability scoring
   - Attendance patterns

---

## 🐛 Troubleshooting

### Worker Can't Login

**Check:**
1. Account exists in Django Admin
2. Account is "Active" and "Approved"
3. Account not locked (check "Locked Until" field)
4. Phone number matches exactly
5. PIN is correct (staff can reset to phone last 4 digits)

### Service Request Photo Won't Upload

**Check:**
1. File is an image format (JPG, PNG, GIF, WEBP)
2. File size < 10MB
3. Azure Blob Storage is configured
4. Check browser console for errors

### Assignments Not Showing

**Check:**
1. Worker has ClientAvailability records
2. WorkAssignment records exist for this client
3. Assignment dates are correct
4. Check browser console for API errors

### Token Errors

**Solution:**
- Logout and login again
- Clear browser localStorage
- Check token in localStorage: `localStorage.getItem('worker_token')`

---

## 📞 Support

For issues or questions:

1. **Technical Issues:** Check Django logs and browser console
2. **Account Problems:** Contact system administrator
3. **Feature Requests:** Submit via GitHub or internal ticketing

---

## 🎉 Success Metrics

Track these KPIs:

- **Worker Engagement:** Daily active users
- **Response Time:** Average time to acknowledge service requests
- **Call-Out Rate:** Percentage of shifts called out
- **Availability Accuracy:** Workers updating schedules regularly
- **Issue Resolution:** Average time to resolve service requests

---

**Built with:** Django 3.2, Django REST Framework, Vue.js 3, TypeScript, Tailwind CSS

**Deployed on:** Azure App Service + Azure Static Web Apps

**Maintained by:** System Administrator

---

*Last Updated: January 2026*
