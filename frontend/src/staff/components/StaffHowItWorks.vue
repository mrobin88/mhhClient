<template>
  <section class="staff-guide">
    <header class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">menu_book</span>
        <h3>How everything works</h3>
      </div>
      <p class="text-sm text-stone-600">
        One page that explains every part of the Mission Hiring Hall system: which app to use for
        what, how a client moves through our programs, and what happens automatically. Read this
        before asking for a change — then file a ticket so nothing gets lost in a hallway
        conversation.
      </p>
    </header>

    <nav class="staff-guide-toc" aria-label="Sections">
      <a v-for="item in sections" :key="item.id" :href="`#${item.id}`">{{ item.label }}</a>
    </nav>

    <article id="apps" class="staff-card p-4 staff-guide-section">
      <h4>Which app do I use?</h4>
      <p class="staff-guide-lead">
        We run several small apps instead of one big one. Each has a different audience.
      </p>
      <div class="staff-guide-list">
        <div v-for="app in apps" :key="app.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ app.name }}</p>
          <p class="staff-guide-item-who">{{ app.who }}</p>
          <p class="staff-guide-item-body">{{ app.what }}</p>
        </div>
      </div>
    </article>

    <article id="path" class="staff-card p-4 staff-guide-section">
      <h4>How a client moves through the system</h4>
      <ol class="staff-guide-steps">
        <li v-for="(step, i) in clientPath" :key="i">
          <span class="staff-guide-step-title">{{ step.title }}</span>
          {{ step.body }}
        </li>
      </ol>
      <p class="staff-guide-note">
        Programs a person can pick at signup: CAPSA, City Build, Pit Stop, Security Guard Card
        Training, and General Employment Assistance. You can change someone's program later on their
        client page.
      </p>
    </article>

    <article id="pitstop" class="staff-card p-4 staff-guide-section">
      <h4>Pit Stop: applicants vs workers</h4>
      <p class="staff-guide-lead">
        This is where spreadsheets used to live. Everyone in Pit Stop has a stage on their client
        page, so you can stop tracking it separately.
      </p>
      <div class="staff-guide-list">
        <div v-for="stage in pitStopStages" :key="stage.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ stage.name }}</p>
          <p class="staff-guide-item-body">{{ stage.body }}</p>
        </div>
      </div>
      <p class="staff-guide-note">
        To find people fast: Clients → tap the <strong>Pit Stop</strong> chip, then a stage chip like
        <strong>Applicants</strong> or <strong>Workers</strong>. To give someone a worker login, open
        their page and use <strong>Give worker portal access</strong> in the Pit Stop box. Their PIN
        is the last 4 digits of their phone.
      </p>
    </article>

    <article id="screens" class="staff-card p-4 staff-guide-section">
      <h4>What each staff screen does</h4>
      <div class="staff-guide-list">
        <div v-for="screen in screens" :key="screen.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ screen.name }}</p>
          <p class="staff-guide-item-body">{{ screen.body }}</p>
          <p v-if="screen.cannot" class="staff-guide-item-limit">Cannot: {{ screen.cannot }}</p>
        </div>
      </div>
    </article>

    <article id="automatic" class="staff-card p-4 staff-guide-section">
      <h4>What happens automatically</h4>
      <div class="staff-guide-list">
        <div v-for="item in automatic" :key="item.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ item.name }}</p>
          <p class="staff-guide-item-body">{{ item.body }}</p>
        </div>
      </div>
    </article>

    <article id="retire" class="staff-card p-4 staff-guide-section">
      <h4>Still here, probably not needed</h4>
      <p class="staff-guide-lead">
        Being honest about the dusty corners. If you never use something on this list, say so in a
        ticket and we will remove it. Fewer moving parts means fewer things to explain to the next
        person.
      </p>
      <div class="staff-guide-list">
        <div v-for="item in retirementCandidates" :key="item.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ item.name }}</p>
          <p class="staff-guide-item-body">{{ item.body }}</p>
        </div>
      </div>
    </article>

    <article id="change" class="staff-card p-4 staff-guide-section">
      <h4>Need something changed?</h4>
      <p class="staff-guide-lead">
        Do not rely on a hallway conversation or a text message — those get lost. File a ticket so
        the request is tracked and you can see its status.
      </p>
      <ol class="staff-guide-steps">
        <li>
          <span class="staff-guide-step-title">Say what you expected.</span>
          For example: "I expected the client list to show their program."
        </li>
        <li>
          <span class="staff-guide-step-title">Say what actually happened.</span>
          Include the person's name or the screen you were on.
        </li>
        <li>
          <span class="staff-guide-step-title">Add a screenshot.</span>
          Open the ticket after you create it and attach a picture — it saves a lot of back and
          forth.
        </li>
        <li>
          <span class="staff-guide-step-title">Set how urgent it is.</span>
          P0 means nobody can work right now. P3 or P4 means it is an annoyance or an idea.
        </li>
      </ol>
      <button
        type="button"
        class="staff-btn staff-btn-primary w-full mt-3"
        @click="router.push({ name: 'Tickets' })"
      >
        Open tickets
      </button>
    </article>
  </section>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const sections = [
  { id: 'apps', label: 'Which app' },
  { id: 'path', label: 'Client path' },
  { id: 'pitstop', label: 'Pit Stop' },
  { id: 'screens', label: 'Staff screens' },
  { id: 'automatic', label: 'Automatic' },
  { id: 'retire', label: 'Not needed?' },
  { id: 'change', label: 'Request a change' },
]

const apps = [
  {
    name: 'Staff workspace (this app)',
    who: 'You, every day',
    what: 'Look people up, fix their info, sign them up for classes, write case notes, read text threads, and file tickets. This should cover most of your day.',
  },
  {
    name: 'Public signup form',
    who: 'Clients, on their own phone or a lobby tablet',
    what: 'The registration form where someone picks a program and enters their info. Pit Stop signups answer a few extra questions.',
  },
  {
    name: 'Lobby check-in',
    who: 'Clients walking in',
    what: 'Someone enters their phone number, picks their name, and says why they came. It writes a case note automatically and can take document photos.',
  },
  {
    name: 'Worker portal',
    who: 'Pit Stop workers',
    what: 'Phone and PIN login for clocking in and out, submitting incident reports, and daily feedback. Only people you have given portal access can use it.',
  },
  {
    name: 'Django admin',
    who: 'Managers and tech',
    what: 'The full database. Everything is editable here, including things the staff workspace deliberately hides. Use it for worker PIN resets, work sites, classes setup, and partner API keys.',
  },
  {
    name: 'Reports hub',
    who: 'Managers',
    what: 'Downloadable CSV and ZIP packages: client outcomes, Pit Stop hours, missing documents, manager package. Log into admin first or the downloads will be blocked.',
  },
  {
    name: 'Partner API docs',
    who: 'Outside organizations',
    what: 'A separate page documenting how a partner organization sends us referrals from their own system. They can only send referrals in — they cannot read our client records.',
  },
]

const clientPath = [
  {
    title: 'They sign up.',
    body: 'Either on the public form, at the lobby kiosk, or you add them in admin. They pick a program.',
  },
  {
    title: 'They become a client record.',
    body: 'Everything else hangs off that one record: notes, documents, classes, texts, and Pit Stop stage.',
  },
  {
    title: 'You meet with them.',
    body: 'Write one case note per meaningful visit. Set the note date if you are catching up on a past day.',
  },
  {
    title: 'They take classes.',
    body: 'Orientation, JRT, and workshops. Sign them up from their client page or from the Classes screen, then mark attendance.',
  },
  {
    title: 'They turn in documents.',
    body: 'ID, resume, consent, intake, and program-specific paperwork. City Build has its own checklist in admin.',
  },
  {
    title: 'Pit Stop only: they may become a worker.',
    body: 'Move them through the Pit Stop stages and give them portal access when they are ready to work shifts.',
  },
]

const pitStopStages = [
  {
    name: 'Applicant',
    body: 'Signed up for Pit Stop but not accepted yet. This is where everyone starts automatically.',
  },
  {
    name: 'Waitlisted',
    body: 'We would take them, but there is no room right now.',
  },
  {
    name: 'Active participant',
    body: 'Accepted and working with us, but not clocking shifts on the portal yet.',
  },
  {
    name: 'Worker',
    body: 'Has a portal login and clocks in and out. This is set automatically the moment you give them portal access — you do not pick it by hand.',
  },
  {
    name: 'Exited',
    body: 'Left the program. Their record and hours stay for reporting.',
  },
]

const screens = [
  {
    name: 'Home',
    body: 'Your starting point: recent signups, upcoming classes, program breakdown, recent staff activity, quick search, and document upload.',
  },
  {
    name: 'Clients',
    body: 'Search by name or phone, and filter by program or Pit Stop stage. Tap a person to open their full record.',
  },
  {
    name: 'Client page',
    body: 'Edit contact info, program, status, and dates. Sign them up for classes, add case notes, and manage Pit Stop stage and portal access.',
    cannot: 'reset a worker PIN or turn portal access back off — that is Django admin.',
  },
  {
    name: 'Messages',
    body: 'Text message threads with clients. The badge counts unread replies.',
    cannot: 'send a new text from here — outgoing texts go out from admin actions and scheduled jobs.',
  },
  {
    name: 'Classes',
    body: 'Create class templates, generate sessions on a schedule, and mark who attended.',
  },
  {
    name: 'Tickets',
    body: 'Report bugs and request changes. Attach screenshots, set urgency, and follow the status.',
  },
  {
    name: 'Skill note',
    body: 'Log a training or skill a client completed. It is a shortcut for one kind of case note.',
  },
]

const automatic = [
  {
    name: 'Check-in notes',
    body: 'When someone checks in at the lobby kiosk, a case note is written for you. You do not need to duplicate it.',
  },
  {
    name: 'Pit Stop stage',
    body: 'Giving someone worker portal access moves them to the Worker stage on its own.',
  },
  {
    name: 'Progress text messages',
    body: 'Check-in texts at 30, 60, 90, and 120 days after intake. These are turned OFF unless tech enables them, so do not assume a client was contacted.',
  },
  {
    name: 'Partner referrals',
    body: 'Partner organizations can send referrals straight into the system. They arrive for staff review — they do not become clients on their own.',
  },
  {
    name: 'Staff assignment',
    body: 'When you save a change on a client, your name is recorded as the assigned staff member.',
  },
]

const retirementCandidates = [
  {
    name: 'Old work assignment scheduling',
    body: 'We used to schedule shifts in the system. Workers now just clock in at a site, so the scheduling screens are switched off and only leftover code remains.',
  },
  {
    name: 'Legacy staff feedback',
    body: 'An older feedback box that tickets replaced. Kept only so the old entries are still readable.',
  },
  {
    name: 'Duplicate report downloads',
    body: 'A couple of CSV exports exist that are not linked anywhere on the reports hub, which usually means nobody uses them.',
  },
  {
    name: 'Overlapping written guides',
    body: 'There were several out-of-date instruction documents. This page is now the real one; the rest point back here.',
  },
]
</script>
