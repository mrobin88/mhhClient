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
        We run several small apps instead of one big one, each for a different audience. Every link
        below opens in a new tab so you keep your place here.
      </p>
      <div class="staff-guide-list">
        <div v-for="app in apps" :key="app.name" class="staff-guide-item">
          <p class="staff-guide-item-title">
            {{ app.name }}
            <span v-if="app.here" class="staff-guide-item-here">You are here</span>
          </p>
          <p class="staff-guide-item-who">{{ app.who }}</p>
          <p class="staff-guide-item-body">{{ app.what }}</p>
          <a
            v-if="app.href"
            :href="app.href"
            target="_blank"
            rel="noopener"
            class="staff-guide-item-link"
          >
            <span class="material-symbols-outlined" aria-hidden="true">open_in_new</span>
            {{ app.linkLabel }}
          </a>
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
import { getApiUrl } from '../../config/api'

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
    name: 'Staff workspace',
    who: 'You, every day',
    what: 'The app you are in right now. Look someone up, fix a wrong phone number, sign them up for a class, write a case note, and read their text replies. If something is part of your normal day and you cannot do it here, that is worth a ticket.',
    here: true,
  },
  {
    name: 'Public signup form',
    who: 'New clients, on their own phone or the lobby tablet',
    what: 'How people register themselves. They pick a program, fill in their details, and can attach a resume or a photo of their ID, though both are optional. Pit Stop applicants answer extra questions about their work history and which shifts they can take. Text someone the link, or leave it open on the tablet.',
    href: '/',
    linkLabel: 'Open the signup form',
  },
  {
    name: 'Lobby check-in',
    who: 'Clients who are already in the system, walking in',
    what: 'They type their phone number, tap their name, and say why they came. A case note is written on their record for you, so you do not have to log the visit yourself. They can also photograph a document they brought with them.',
    href: '/checkin',
    linkLabel: 'Open lobby check-in',
  },
  {
    name: 'Worker portal',
    who: 'Pit Stop workers',
    what: 'Phone number and a 4-digit PIN, no email needed. Workers clock in and out at a site, file incident reports, and send daily feedback. Only people you have given portal access can sign in, and their PIN is the last 4 digits of their phone.',
    href: '/worker/',
    linkLabel: 'Open the worker portal',
  },
  {
    name: 'Django admin',
    who: 'Managers and tech',
    what: 'The raw database with nothing hidden. Go here for what this workspace deliberately leaves out: resetting a worker PIN, switching portal access back off, adding work sites, and repairing a record that was saved wrong. There is no undo, so change one thing at a time.',
    href: getApiUrl('/admin/'),
    linkLabel: 'Open Django admin',
  },
  {
    name: 'Reports hub',
    who: 'Managers',
    what: 'Spreadsheets you can download: client outcomes, Pit Stop hours, who is still missing documents, and the whole manager package as one ZIP. Sign into Django admin first in the same browser or the download gets refused.',
    href: getApiUrl('/api/reports/'),
    linkLabel: 'Open the reports hub',
  },
]

const clientPath = [
  {
    title: 'They sign up.',
    body: 'They use the public form, or staff use Add a client on the dashboard for an outside referral or interest form.',
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
    body: 'Orientation, JRT, and workshops. Sign them up from their client page, then mark attendance on the Classes screen.',
  },
  {
    title: 'They turn in documents.',
    body: 'ID, resume, consent, intake, and program-specific paperwork. From their client page, select missing City Build documents and send an expiring secure upload link.',
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
    body: 'Your starting point: add a client from an outside referral, review recent signups and classes, search, and upload staff-received documents.',
  },
  {
    name: 'Clients',
    body: 'Search by name or phone, and filter by program or Pit Stop stage. Tap a person to open their full record.',
  },
  {
    name: 'Client page',
    body: 'Edit contact info, program, status, and dates. Sign them up for classes, add case notes, and create scoped document-upload links for outreach.',
    cannot: 'reset a worker PIN or turn portal access back off — that is Django admin.',
  },
  {
    name: 'Messages',
    body: 'Text message threads with clients. The badge counts unread replies.',
    cannot: 'send a new text from here — the only text that goes out is the class confirmation when you sign someone up.',
  },
  {
    name: 'Classes',
    body: 'Create and edit Orientation, JRT, and other class templates. Edit or cancel dated sessions, generate recurring dates, and mark attendance.',
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
    name: 'Class confirmation text',
    body: 'When you add someone to a class, they get a text with the date, time, and place. You see the exact message on their client page before you press Add, and it tells you if no text is going out. This is the only text the app sends on its own.',
  },
  {
    name: 'Progress text messages',
    body: 'Check-in texts at 30, 60, 90, and 120 days after intake. These are turned OFF, so do not assume a client was contacted.',
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
