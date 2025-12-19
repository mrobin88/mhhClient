# Case Notes System Guide

## Overview

The case notes system has been improved to make it clear that **each case note should be a separate entry**. Each dated entry (e.g., "09/02/2025...", "09/09/2025...") should be created as a **separate case note**, not all in one text box.

## Key Features

### 1. **Separate Entries**
- Each case note is now displayed as a separate row in the admin
- Each row represents ONE case note entry
- Use the "Add another Case Note" button to create multiple entries

### 2. **Visual Indicators**
- **Overdue follow-ups** are highlighted in red
- **Due soon** (within 3 days) are highlighted in orange
- **On track** follow-ups show a green checkmark

### 3. **Quick Add Case Note**
- Click "Add Case Note" button when viewing a client
- Quick form to add a new case note
- Shows recent case notes for reference

### 4. **Email Alerts**
- Automatic email alerts for follow-up dates
- Alerts sent when follow-ups are due or overdue
- Emails include client info, note content, and direct link to admin

## How to Use

### Adding Case Notes

**Option 1: Inline on Client Page**
1. Go to Admin → Clients → Select a client
2. Scroll to "Case Notes Timeline" section
3. Click "Add another Case Note" button
4. Fill in:
   - Staff Member
   - Note Type (Intake, Follow-up, Training, etc.)
   - Content (ONE entry per row)
   - Next Steps (optional)
   - Follow-up Date (optional)
5. Click "Save"

**Option 2: Quick Add Form**
1. Go to Admin → Clients → Select a client
2. Click the **"➕ Add Case Note"** button at the top right of the page
3. Fill in the form:
   - Note Type (Required)
   - Content (Required - ONE entry per case note)
   - Next Steps (Optional)
   - Follow-up Date (Optional)
4. Click "Add Case Note"
5. You'll be redirected back to the client page with your new case note visible in the timeline

### Setting Follow-up Dates

1. When creating or editing a case note, set a "Follow-up Date"
2. You'll receive email alerts when:
   - The follow-up date is 1 day away (configurable)
   - The follow-up date has passed (overdue)

### Email Alert System

#### Setup

1. **Configure Email Settings** in your environment variables:
   ```bash
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   DEFAULT_FROM_EMAIL=noreply@missionhiringhall.org
   CASE_NOTE_ALERT_EMAIL=alerts@missionhiringhall.org  # Fallback email
   ADMIN_BASE_URL=https://your-backend-url.azurewebsites.net
   ```

2. **Set up Scheduled Task** (cron or Azure WebJobs):
   ```bash
   # Run daily at 9 AM
   0 9 * * * cd /path/to/backend && python manage.py send_followup_alerts
   ```

#### Manual Testing

**Test the email system:**
```bash
# Dry run (see what would be sent)
python manage.py send_followup_alerts --dry-run

# Send alerts for overdue only
python manage.py send_followup_alerts --overdue-only

# Send alerts for follow-ups due in next 3 days
python manage.py send_followup_alerts --days-before 3
```

**Send alerts from Admin:**
1. Go to Admin → Case Notes
2. Select case notes with follow-up dates
3. Choose "Send follow-up alert emails" from Actions dropdown
4. Click "Go"

## Important Notes

### ⚠️ DO NOT:
- Put multiple dated entries in ONE case note's content field
- Example of WRONG usage:
  ```
  Content: "09/02/2025 Referral Date... 09/09/2025 Intake... 09/15/2025 First day..."
  ```

### ✅ DO:
- Create separate case notes for each date/entry
- Example of CORRECT usage:
  - Case Note 1: "09/02/2025 Referral Date..."
  - Case Note 2: "09/09/2025 Intake..."
  - Case Note 3: "09/15/2025 First day..."

## Email Alert Details

### Who Receives Alerts?
- The staff member who created the case note (if their email is in the system)
- Fallback: Admin email or `CASE_NOTE_ALERT_EMAIL` setting

### Alert Timing
- Default: Alerts sent 1 day before follow-up date
- Overdue: Alerts sent daily for overdue follow-ups
- Configurable via `--days-before` parameter

### Email Content
- Client information
- Case note details
- Follow-up status (due soon or overdue)
- Direct link to edit case note in admin
- Note content and next steps

## Troubleshooting

### Emails Not Sending
1. Check email settings in environment variables
2. Verify SMTP credentials are correct
3. Check logs: `python manage.py send_followup_alerts --dry-run`
4. Ensure user emails are set in StaffUser model

### Case Notes Not Showing Separately
- Make sure you're using "Add another Case Note" button
- Each row = one case note entry
- Don't put multiple dates in one content field

### Follow-up Alerts Not Working
1. Verify follow-up dates are set on case notes
2. Check scheduled task is running
3. Test manually: `python manage.py send_followup_alerts`
4. Check email logs for errors

## Support

For issues or questions, check:
- Admin interface help text
- This guide
- System logs for errors

