<template>
  <section class="staff-guide">
    <header class="staff-card p-4">
      <div class="staff-panel-header">
        <span class="material-symbols-outlined" aria-hidden="true">menu_book</span>
        <h3>How everything works</h3>
      </div>
      <p class="text-sm text-stone-600">
        Short map of the apps and screens. Day-to-day work stays in this staff dashboard. For
        one-off repairs, PINs, work sites, and anything this workspace leaves out, use Django admin.
      </p>
    </header>

    <nav class="staff-guide-toc" aria-label="Sections">
      <button
        v-for="item in sections"
        :key="item.id"
        type="button"
        @click="scrollToSection(item.id)"
      >
        {{ item.label }}
      </button>
    </nav>

    <article id="apps" class="staff-card p-4 staff-guide-section">
      <h4>Which app</h4>
      <p class="staff-guide-lead">Staff screens stay in this dashboard. Other apps and Django open in a new tab.</p>
      <div class="staff-guide-list">
        <div v-for="app in apps" :key="app.name" class="staff-guide-item">
          <p class="staff-guide-item-title">
            {{ app.name }}
            <span v-if="app.here" class="staff-guide-item-here">You are here</span>
          </p>
          <p class="staff-guide-item-who">{{ app.who }}</p>
          <p class="staff-guide-item-body">{{ app.what }}</p>
          <div v-if="app.links?.length" class="staff-guide-item-links">
            <GuideLink v-for="link in app.links" :key="link.label" :link="link" />
          </div>
        </div>
      </div>
    </article>

    <article id="screens" class="staff-card p-4 staff-guide-section">
      <h4>Staff screens</h4>
      <div class="staff-guide-list">
        <div v-for="screen in screens" :key="screen.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ screen.name }}</p>
          <p class="staff-guide-item-body">{{ screen.body }}</p>
          <div class="staff-guide-item-links">
            <GuideLink v-for="link in screen.links" :key="link.label" :link="link" />
          </div>
        </div>
      </div>
    </article>

    <article id="path" class="staff-card p-4 staff-guide-section">
      <h4>Client path</h4>
      <ol class="staff-guide-steps">
        <li v-for="(step, i) in clientPath" :key="i">
          <span class="staff-guide-step-title">{{ step.title }}</span>
          {{ step.body }}
        </li>
      </ol>
      <p class="staff-guide-note">
        Programs at signup: CAPSA, City Build, Pit Stop, Security Guard Card Training, and General
        Employment Assistance. Change program later from the client page.
      </p>
    </article>

    <article id="pitstop" class="staff-card p-4 staff-guide-section">
      <h4>Pit Stop</h4>
      <p class="staff-guide-lead">
        New applications land on Pit Stop apps. Read the digital form, resume, and program
        answers there — that replaced the paper stack. Stage still lives on the client page.
        Portal access is granted from the Pit Stop box on their page.
      </p>
      <div class="staff-guide-list">
        <div v-for="stage in pitStopStages" :key="stage.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ stage.name }}</p>
          <p class="staff-guide-item-body">{{ stage.body }}</p>
        </div>
      </div>
      <div class="staff-guide-item-links">
        <GuideLink :link="{ to: '/pitstop-applications', label: 'Open Pit Stop applications' }" />
        <GuideLink :link="{ to: '/clients', label: 'Open Clients' }" />
        <GuideLink :link="{ href: workerAdminUrl, label: 'Django: worker accounts' }" />
      </div>
    </article>

    <article id="citybuild" class="staff-card p-4 staff-guide-section">
      <h4>City Build</h4>
      <p class="staff-guide-lead">
        Stage lives on the client page when the program is City Build. Public signup lists
        upcoming classes whose Program is City Build — set that on Classes so people can pick
        a date. Accepted and Dropped are pre-registration. Enrolled and Arrived mean they are
        in the CBA 12-week program. In the running means it is time for the file packet.
        Drug-test result is not stored.
      </p>
      <div class="staff-guide-list">
        <div v-for="stage in cityBuildStages" :key="stage.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ stage.name }}</p>
          <p class="staff-guide-item-body">{{ stage.body }}</p>
        </div>
      </div>
      <div class="staff-guide-item-links">
        <GuideLink :link="{ to: '/clients', label: 'Open Clients' }" />
      </div>
    </article>

    <article id="django" class="staff-card p-4 staff-guide-section">
      <h4>Django admin</h4>
      <p class="staff-guide-lead">
        Use this when the staff screens are not enough. Change one thing at a time.
      </p>
      <div class="staff-guide-list">
        <div v-for="item in djangoLinks" :key="item.name" class="staff-guide-item">
          <p class="staff-guide-item-title">{{ item.name }}</p>
          <p class="staff-guide-item-body">{{ item.body }}</p>
          <GuideLink :link="{ href: item.href, label: item.linkLabel }" />
        </div>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
import { getApiUrl } from '../../config/api'
import GuideLink from './GuideLink.vue'

const workerAdminUrl = getApiUrl('/admin/clients/workeraccount/')

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const sections = [
  { id: 'apps', label: 'Which app' },
  { id: 'screens', label: 'Staff screens' },
  { id: 'path', label: 'Client path' },
  { id: 'pitstop', label: 'Pit Stop' },
  { id: 'citybuild', label: 'City Build' },
  { id: 'django', label: 'Django admin' },
]

const apps = [
  {
    name: 'Staff workspace',
    who: 'You, every day',
    what: 'Search someone at the top of Home, see their info, add them to a class, leave a note. Feedback is always on the bottom bar.',
    here: true,
    links: [{ to: '/dashboard', label: 'Open Home' }],
  },
  {
    name: 'Public signup',
    who: 'New clients',
    what: 'Home page asks Check In or Sign Up. Signup is self-register, pick a program, optionally attach a resume or ID photo. Pit Stop requires a resume, work history, and a few questions about the workforce program.',
    links: [
      { href: '/', label: 'Open client portal' },
      { href: '/signup', label: 'Open signup form' },
    ],
  },
  {
    name: 'Lobby check-in',
    who: 'Clients already in the system',
    what: 'Phone number, tap their name, say why they came. Writes a case note for you.',
    links: [{ href: '/checkin/', label: 'Open lobby check-in' }],
  },
  {
    name: 'Worker portal',
    who: 'Pit Stop workers',
    what: 'Clock in and out, incident reports, daily feedback. Only people given portal access can sign in.',
    links: [{ href: '/worker/', label: 'Open worker portal' }],
  },
  {
    name: 'Django admin',
    who: 'Managers and tech',
    what: 'Reset a worker PIN, turn portal access off, add work sites, repair a record.',
    links: [{ href: getApiUrl('/admin/'), label: 'Open Django admin' }],
  },
  {
    name: 'Reports hub',
    who: 'Managers',
    what: 'Downloadable spreadsheets. Sign into Django admin in the same browser first or the download is refused.',
    links: [{ href: getApiUrl('/api/reports/'), label: 'Open reports hub' }],
  },
]

const screens = [
  {
    name: 'Home',
    body: 'Search at the top by name or phone, see their info, add them to a class, and leave a note. Feedback is always on the bar at the bottom. The Menu opens the rest of the screens.',
    links: [{ to: '/dashboard', label: 'Open Home' }],
  },
  {
    name: 'Clients',
    body: 'The roster. Search, filter by program or stage, then open someone.',
    links: [{ to: '/clients', label: 'Open Clients' }],
  },
  {
    name: 'Pit Stop applications',
    body: 'Read the full digital application, resume, and program answers. Update review status and notes here. Print a copy for the file.',
    links: [{ to: '/pitstop-applications', label: 'Open Pit Stop applications' }],
  },
  {
    name: 'Client page',
    body: 'See who they are, call or text, add them to a class, and leave a note. Contact and program details are further down if something needs fixing.',
    links: [
      { to: '/clients', label: 'Open Clients' },
      { href: getApiUrl('/admin/clients/client/'), label: 'Django: client records' },
    ],
  },
  {
    name: 'Messages',
    body: 'Text threads with clients. Unread replies show as a badge. Automated texts are informational class signup notices, class changes, removals, cancellations, and a thank-you after a Pit Stop application. YES or STOP replies are not acted on in this system.',
    links: [{ to: '/messages', label: 'Open Messages' }],
  },
  {
    name: 'Classes',
    body: 'The calendar shows class dates as boxes. Click a box for the name list, mark who is here, and print a roster with space for notes. Classes are grouped by program (City Build, Pit Stop, CAPSA, Guard Card, General). Removing someone texts that we are working on a new date. Cancel keeps the date; delete removes it.',
    links: [{ to: '/classes', label: 'Open Classes' }],
  },
  {
    name: 'Suggestion box',
    body: 'Feedback is on every screen: the lightbulb next to Menu, and Feedback at the top. It records which page you were on. Open the box to see everyone’s notes or add a screenshot.',
    links: [{ to: '/suggestions', label: 'Open suggestion box' }],
  },
  {
    name: 'Skill note',
    body: 'Log a completed training. Shortcut for one kind of case note.',
    links: [{ to: '/create-skill', label: 'Open Skill note' }],
  },
]

const clientPath = [
  { title: 'They sign up.', body: 'Public form, or Add a client on Home for an outside referral.' },
  { title: 'They become a record.', body: 'Notes, documents, classes, texts, Pit Stop stage, and City Build stage hang off that one page.' },
  { title: 'You meet with them.', body: 'One case note per meaningful visit. If nobody has reached out for 3 weeks, Teams (MHH ALL STAFF) gets a message with their name and what they applied for.' },
  { title: 'Classes and documents.', body: 'Sign up from their page. Mark attendance and print a roster on Classes. Send an upload link for missing paperwork.' },
  { title: 'Pit Stop workers.', body: 'Move stages, then grant portal access when they are ready for shifts.' },
]

const pitStopStages = [
  { name: 'Applicant', body: 'Signed up, not accepted yet. Default starting stage.' },
  { name: 'Waitlisted', body: 'We would take them; no room right now.' },
  { name: 'Active participant', body: 'Accepted, not clocking shifts yet.' },
  { name: 'Worker', body: 'Set automatically when you grant portal access.' },
  { name: 'Exited', body: 'Left the program. Record and hours stay for reporting.' },
]

const cityBuildStages = [
  { name: 'Pre-registration', body: 'General interest, interview scheduled/completed, drug test (no result stored), in the running (file submission), waitlisted, accepted, dropped.' },
  { name: 'CBA 12-week', body: 'Enrolled, arrived, and completed. This is the program itself, after pre-registration.' },
]

const djangoLinks = [
  {
    name: 'Django home',
    body: 'Starting point for anything the staff screens cannot do.',
    href: getApiUrl('/admin/'),
    linkLabel: 'Open Django admin',
  },
  {
    name: 'Worker accounts',
    body: 'Reset a PIN, turn portal access off, or repair a worker login.',
    href: workerAdminUrl,
    linkLabel: 'Open worker accounts',
  },
  {
    name: 'Work sites',
    body: 'Add or edit clock-in sites.',
    href: getApiUrl('/admin/clients/worksite/'),
    linkLabel: 'Open work sites',
  },
  {
    name: 'Client records',
    body: 'Full record repair when the staff client page is not enough.',
    href: getApiUrl('/admin/clients/client/'),
    linkLabel: 'Open client records',
  },
]
</script>
