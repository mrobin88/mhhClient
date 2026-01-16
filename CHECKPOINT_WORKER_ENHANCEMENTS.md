# Worker Portal Enhancement Checkpoint
**Status**: Awaiting User Feedback  
**Priority**: High (Addresses payroll fraud + accountability)  
**Created**: 2026-01-15

---

## 1. On-Call Person / Supervisor SMS Notifications

### Problem
- Supervisors need real-time alerts for:
  - New assignments created
  - Worker call-outs
  - Service requests submitted
  - Workers clocking in late/not showing up

### Solution
**On-Call Person Designation**
- Admin can set "on-call" supervisor per work site or shift
- On-call person receives SMS for:
  - Assignments scheduled within next 24 hours
  - Call-outs (with advance notice time)
  - Urgent service requests (safety, broken equipment)
  - No-shows (worker didn't clock in within 15 min of shift start)

### Technical Implementation
```python
# New Model: OnCallSchedule
class OnCallSchedule(models.Model):
    supervisor = ForeignKey(User)  # Staff member on-call
    work_site = ForeignKey(WorkSite, null=True, blank=True)  # Specific site or all sites
    start_datetime = DateTimeField()
    end_datetime = DateTimeField()
    phone_number = CharField(max_length=20)  # SMS destination
    notification_types = JSONField(default=list)  # ['call_out', 'service_request', 'no_show', 'late']
    is_active = BooleanField(default=True)
```

**SMS Triggers**:
- Worker clocks in → No SMS (all good)
- Worker clocks in 10+ min late → SMS: "Tom late to Mission Pit Stop (10 min)"
- Worker doesn't clock in within 15 min → SMS: "Tom NO SHOW at Mission Pit Stop"
- Worker calls out → SMS: "Tom called out Mission Pit Stop (8hr notice): sick"
- Urgent service request → SMS: "URGENT: Safety issue at Mission Pit Stop - Tom"

**Django Celery Tasks**:
- `check_upcoming_shifts` (runs every 5 min) → SMS reminders 1 hour before shift
- `check_no_shows` (runs every 5 min) → SMS alert if clock-in missed
- `notify_on_call_supervisor` (triggered by events)

**SMS Service**: Twilio integration (already configured for client SMS)

---

## 2. Clock In/Out System with GPS Verification

### Problem
- No way to track actual hours worked
- Workers could claim hours without showing up
- No proof they were at the location

### Solution
**GPS-Verified Clock In/Out**

#### Frontend (Worker Portal)
```typescript
// New component: ClockInOut.vue
- Big "🕐 Clock In" button on dashboard (if shift is today)
- Captures GPS coordinates when clicked
- Shows countdown timer while clocked in
- "🕐 Clock Out" button to end shift
- Offline support: Queue clock-in/out, sync when signal returns
```

#### Backend
```python
# New Model: WorkerClockEvent
class WorkerClockEvent(models.Model):
    EVENT_TYPES = [
        ('clock_in', 'Clock In'),
        ('clock_out', 'Clock Out'),
        ('break_start', 'Break Start'),
        ('break_end', 'Break End'),
    ]
    
    worker = ForeignKey(Client, related_name='clock_events')
    assignment = ForeignKey(WorkAssignment)
    event_type = CharField(max_length=20, choices=EVENT_TYPES)
    timestamp = DateTimeField(auto_now_add=True)
    
    # GPS Verification
    latitude = DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = DecimalField(max_digits=9, decimal_places=6, null=True)
    gps_accuracy = DecimalField(max_digits=6, decimal_places=2, null=True)  # meters
    
    # Location Verification
    is_within_geofence = BooleanField(default=False)
    distance_from_site = DecimalField(max_digits=8, decimal_places=2, null=True)  # meters
    
    # Fraud Detection
    flagged_as_suspicious = BooleanField(default=False)
    flag_reason = CharField(max_length=200, blank=True)
    
    # Device Info (for pattern detection)
    device_id = CharField(max_length=100, blank=True)
    ip_address = GenericIPAddressField(null=True)
    user_agent = CharField(max_length=255, blank=True)
```

#### GPS Geofencing Logic
```python
def verify_clock_event(clock_event: WorkerClockEvent) -> bool:
    """
    Verify worker is at correct location.
    Returns True if valid, False if suspicious.
    """
    work_site = clock_event.assignment.work_site
    site_lat = work_site.latitude
    site_lon = work_site.longitude
    
    # Calculate distance from work site
    distance = haversine_distance(
        clock_event.latitude, clock_event.longitude,
        site_lat, site_lon
    )
    
    clock_event.distance_from_site = distance
    
    # Geofence radius: 100 meters (1 city block)
    GEOFENCE_RADIUS = 100  # meters
    
    if distance <= GEOFENCE_RADIUS:
        clock_event.is_within_geofence = True
        return True
    
    # Flag suspicious events
    if distance > 500:  # More than 5 blocks away
        clock_event.flagged_as_suspicious = True
        clock_event.flag_reason = f"Location {distance}m from site (expected <{GEOFENCE_RADIUS}m)"
        
        # Alert on-call supervisor
        notify_on_call_supervisor(
            clock_event.assignment.work_site,
            f"⚠️ {clock_event.worker.full_name} clocked in {distance}m away from site"
        )
        return False
    
    # Within 100-500m: Warning but allowed (might be parking, etc)
    clock_event.is_within_geofence = False
    clock_event.flag_reason = f"Close but outside geofence ({distance}m)"
    return True
```

#### Fraud Detection Patterns
```python
# Admin Dashboard: Suspicious Activity Report
def detect_fraud_patterns():
    """
    Flag suspicious clock-in patterns for review
    """
    patterns = []
    
    # Pattern 1: Clock-in from same GPS for multiple sites
    # (Worker not actually at location, GPS spoofed/cached)
    
    # Pattern 2: Clock-in within 1 minute of shift start consistently
    # (Likely not actually there, just clicking button)
    
    # Pattern 3: Clock-in/out from home address
    # (Check against client's address on file)
    
    # Pattern 4: Multiple workers clock-in from exact same GPS
    # (One person clocking in for others)
    
    # Pattern 5: Clock events without GPS data
    # (GPS disabled, suspicious)
    
    # Pattern 6: Clock-in but assignment marked "no show" by supervisor
    # (Conflict - investigate)
    
    return patterns
```

---

## 3. Hours Worked Tracking & Reporting

### Problem
- Workers can't see hours worked
- No way to verify payroll
- Supervisors manually track hours

### Solution

#### Worker View: "My Hours" Page
```typescript
// New component: WorkerHours.vue
interface HoursData {
  current_week: {
    total_hours: number
    clocked_shifts: Shift[]
    pending_shifts: Shift[]  // Scheduled but not yet worked
  }
  last_pay_period: {
    total_hours: number
    gross_pay: number  // hours * rate
  }
  this_month: {
    total_hours: number
    days_worked: number
  }
}
```

**Display**:
- Current week: "16.5 hours" (with breakdown by day)
- Last 2 weeks: "Total: 32 hours"
- This month: "Total: 67 hours across 15 days"
- Each shift shows:
  - Date, site, scheduled time
  - Actual clock-in/out time
  - Duration
  - Status: ✅ Verified, ⚠️ Pending Approval, 🚫 Flagged

#### Backend: Hours Calculation
```python
class WorkerHoursService:
    """
    Calculate hours worked from clock events
    """
    
    @staticmethod
    def calculate_shift_hours(assignment: WorkAssignment) -> dict:
        """
        Calculate actual hours worked for a shift
        """
        clock_in = WorkerClockEvent.objects.filter(
            assignment=assignment,
            event_type='clock_in'
        ).first()
        
        clock_out = WorkerClockEvent.objects.filter(
            assignment=assignment,
            event_type='clock_out'
        ).first()
        
        if not clock_in or not clock_out:
            return {
                'status': 'incomplete',
                'hours': 0,
                'issue': 'Missing clock in/out'
            }
        
        # Calculate duration
        duration = clock_out.timestamp - clock_in.timestamp
        hours = duration.total_seconds() / 3600
        
        # Subtract breaks (if tracked)
        breaks = WorkerClockEvent.objects.filter(
            assignment=assignment,
            event_type__in=['break_start', 'break_end']
        ).order_by('timestamp')
        
        break_hours = calculate_break_time(breaks)
        worked_hours = hours - break_hours
        
        # Flag if significantly different from scheduled
        scheduled_hours = (assignment.end_time.hour - assignment.start_time.hour)
        if abs(worked_hours - scheduled_hours) > 1:  # More than 1 hour difference
            return {
                'status': 'flagged',
                'hours': worked_hours,
                'scheduled_hours': scheduled_hours,
                'issue': f'Worked {worked_hours:.1f}h but scheduled for {scheduled_hours}h'
            }
        
        return {
            'status': 'verified',
            'hours': worked_hours,
            'scheduled_hours': scheduled_hours,
            'clock_in_location_valid': clock_in.is_within_geofence,
            'clock_out_location_valid': clock_out.is_within_geofence,
        }
```

#### Supervisor Dashboard: Hours Approval
- Weekly timesheet view (all workers)
- Flag suspicious entries:
  - ⚠️ GPS outside geofence
  - ⚠️ Hours don't match schedule
  - ⚠️ No clock-out recorded
- Bulk approve/reject
- Export to payroll CSV

---

## 4. Anti-Fraud Measures

### Red Flags System

#### Automatic Flags
1. **GPS Spoofing**: Same coordinates used for multiple different sites
2. **Time Padding**: Consistently clocking in early or out late
3. **Pattern Abuse**: Always clocking in/out at exact scheduled time (suspicious consistency)
4. **Buddy Punching**: Multiple workers clocking in from same device/IP
5. **No GPS Data**: Location services disabled
6. **Impossible Travel**: Clock-out at Site A, clock-in at Site B 10 min later (50 miles apart)

#### Manual Review Queue
```python
# Django Admin: Flagged Events
@admin.register(WorkerClockEvent)
class ClockEventAdmin(admin.ModelAdmin):
    list_display = ['worker', 'assignment', 'event_type', 'timestamp', 'flag_status', 'distance_from_site']
    list_filter = ['flagged_as_suspicious', 'is_within_geofence', 'event_type']
    actions = ['approve_flagged_events', 'reject_flagged_events', 'mark_as_fraud']
    
    def flag_status(self, obj):
        if obj.flagged_as_suspicious:
            return format_html('<span style="color: red;">🚫 {}</span>', obj.flag_reason)
        elif not obj.is_within_geofence:
            return format_html('<span style="color: orange;">⚠️ Outside geofence</span>')
        return format_html('<span style="color: green;">✅ Verified</span>')
```

---

## 5. Implementation Priority

### Phase 1 (Critical - Payroll Integrity)
1. Clock in/out with GPS ✅ **MUST HAVE**
2. Hours calculation & display
3. Basic geofencing (100m radius)
4. Flag events outside geofence

### Phase 2 (Fraud Prevention)
1. Fraud pattern detection
2. Admin review dashboard
3. Automated alerts for suspicious activity
4. Bulk approval workflow

### Phase 3 (Supervisor Tools)
1. On-call person designation
2. SMS notifications
3. Real-time shift monitoring
4. No-show auto-detection

---

## 6. Legal & Compliance Notes

### Labor Law Compliance
- Must allow workers to clock in up to 5 min early (CA labor law)
- Breaks must be tracked if shifts > 5 hours
- Overtime auto-calculated for hours > 8/day or 40/week
- Workers must be able to contest flagged hours

### Privacy
- GPS data only collected during shifts
- Workers must consent to location tracking (add to onboarding)
- GPS data retained for payroll dispute resolution (7 years CA requirement)
- No tracking outside work hours

### Data Storage
- Clock events: Permanent (payroll record)
- GPS coordinates: 7 years then purge
- Flagged events: Permanent (audit trail)

---

## 7. API Endpoints (New)

```python
# Worker Portal API
POST /api/worker/clock-in/
POST /api/worker/clock-out/
GET  /api/worker/hours/current-week/
GET  /api/worker/hours/pay-period/<period_id>/
GET  /api/worker/hours/history/

# Admin API
GET  /api/admin/timesheets/pending-approval/
POST /api/admin/timesheets/approve/
POST /api/admin/timesheets/reject/
GET  /api/admin/fraud-alerts/
POST /api/admin/on-call-schedule/
```

---

## 8. Testing Strategy

### GPS Accuracy Testing
- Test in downtown SF (tall buildings, poor GPS)
- Test in parks (good GPS, wide open)
- Test in underground restrooms (no GPS)
- Test with airplane mode → delayed sync

### Fraud Simulation
- Attempt to clock in from home
- Attempt to clock in for multiple people
- Attempt GPS spoofing (mock location app)
- Attempt to clock in without assignment

### Edge Cases
- Worker forgets to clock out → Auto clock-out at scheduled end time + flag
- Phone dies mid-shift → Allow manual entry by supervisor
- No GPS signal at site → Fallback to network location + flag for review
- Worker legitimately needs to leave site briefly → Break feature

---

## 9. Success Metrics

### Adoption
- 90%+ of shifts have clock-in/out within 30 days
- <5% of workers never use clock feature (address with training)

### Fraud Reduction
- <2% of clock events flagged as suspicious
- 0 confirmed payroll fraud incidents

### Supervisor Satisfaction
- Supervisors spend <30 min/week on timesheet approval
- SMS alerts reduce no-show chaos

### Worker Satisfaction
- Workers can verify their hours before payday
- Reduced payroll disputes

---

## Next Steps (Post User Feedback)

1. **Gather feedback** from 5-10 pilot workers
2. Prioritize features based on pain points
3. Build Phase 1 (clock in/out + GPS)
4. Run 2-week pilot with 1-2 work sites
5. Iterate based on pilot data
6. Roll out to all workers

---

**Questions to Answer with User Feedback**:
- Do workers have smartphones with GPS?
- Is cell signal reliable at work sites?
- Do workers understand GPS verification concept?
- Will Spanish translation be needed?
- Do supervisors have time to review flagged events?
