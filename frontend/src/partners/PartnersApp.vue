<template>
  <div class="pc-shell">
    <header class="pc-top">
      <a class="pc-top-brand" href="#overview">
        <span class="pc-top-title">Mission Hiring Hall</span>
        <span class="pc-top-meta">Partner API docs</span>
      </a>
      <a class="pc-top-link" :href="mailtoHref">Request API access</a>
    </header>

    <div class="pc-layout">
      <aside class="pc-toc" aria-label="On this page">
        <p class="pc-toc-label">On this page</p>
        <nav>
          <a
            v-for="item in toc"
            :key="item.id"
            :href="`#${item.id}`"
            :class="{ 'is-active': activeSection === item.id }"
          >{{ item.label }}</a>
        </nav>
      </aside>

      <main class="pc-doc">
        <nav class="pc-mobile-toc" aria-label="Sections">
          <a v-for="item in toc" :key="`m-${item.id}`" :href="`#${item.id}`">{{ item.label }}</a>
        </nav>

        <section id="overview">
          <h1>Partner Referral API</h1>
          <p class="pc-lead">
            Write-only ingest for partner systems (Airtable, Zapier, Make, custom scripts).
            Authenticated partners can create or update referrals. They cannot list or read
            Mission Hiring Hall client records.
          </p>
          <div class="pc-callout">
            <strong>Scope.</strong>
            This surface is intentionally narrow: one <code>POST</code> endpoint, a fixed JSON
            schema, and no sensitive fields (no SSN, no full case file).
          </div>
        </section>

        <section id="base-url">
          <h2>Base URL</h2>
          <div class="pc-pre-wrap">
            <pre class="pc-pre">{{ baseUrl }}</pre>
            <button type="button" class="pc-copy" @click="copyText(baseUrl, 'base')">{{ copyLabel('base') }}</button>
          </div>
          <p>
            All paths below are relative to this host. Production traffic should use HTTPS only.
          </p>
        </section>

        <section id="auth">
          <h2>Authentication</h2>
          <p>
            Each partner organization receives a single API key. Keys are issued by MHH staff and
            shown once. Inactive partners are rejected immediately.
          </p>
          <p>Send the key on every request using either header:</p>
          <div class="pc-pre-wrap">
            <pre class="pc-pre">Authorization: Bearer {{ keyPlaceholder }}
# or
X-Api-Key: {{ keyPlaceholder }}</pre>
            <button
              type="button"
              class="pc-copy"
              @click="copyText(`Authorization: Bearer ${keyPlaceholder}`, 'auth')"
            >
              {{ copyLabel('auth') }}
            </button>
          </div>
          <ul>
            <li>Do not embed keys in public frontends or shared spreadsheets.</li>
            <li>Rotate by asking MHH to generate a new key (old key stops working).</li>
            <li>Missing or invalid keys return <span class="pc-status">401</span>.</li>
          </ul>
        </section>

        <section id="endpoint">
          <h2>Create or update a referral</h2>
          <div class="pc-endpoint">
            <span class="pc-method">POST</span>
            <span class="pc-path">/api/partners/v1/referrals/</span>
          </div>
          <p>
            Creates a referral for staff review, or updates an existing one when
            <code>external_id</code> already exists for your partner.
          </p>
          <p>
            <strong>Methods:</strong> <code>POST</code> only.
            <code>GET</code>, <code>PUT</code>, <code>PATCH</code>, and <code>DELETE</code> return
            <span class="pc-status">405</span>.
          </p>

          <h3>Headers</h3>
          <div class="pc-table-wrap">
            <table class="pc-table">
              <thead>
                <tr>
                  <th>Header</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>Authorization</code></td>
                  <td><code>Bearer &lt;api_key&gt;</code></td>
                </tr>
                <tr>
                  <td><code>Content-Type</code></td>
                  <td><code>application/json</code></td>
                </tr>
              </tbody>
            </table>
          </div>

          <h3>Request body</h3>
          <div class="pc-table-wrap">
            <table class="pc-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Type</th>
                  <th></th>
                  <th>Notes</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>external_id</code></td>
                  <td>string</td>
                  <td><span class="pc-badge pc-badge-req">required</span></td>
                  <td>Your stable id (e.g. Airtable <code>record.id</code>). Max 120 chars. Used for idempotency.</td>
                </tr>
                <tr>
                  <td><code>first_name</code></td>
                  <td>string</td>
                  <td><span class="pc-badge pc-badge-req">required</span></td>
                  <td>Max 100 chars.</td>
                </tr>
                <tr>
                  <td><code>last_name</code></td>
                  <td>string</td>
                  <td><span class="pc-badge pc-badge-req">required</span></td>
                  <td>Max 100 chars.</td>
                </tr>
                <tr>
                  <td><code>phone</code></td>
                  <td>string</td>
                  <td><span class="pc-badge pc-badge-opt">optional*</span></td>
                  <td>Digits preferred. Provide <code>phone</code> or <code>email</code> (or both).</td>
                </tr>
                <tr>
                  <td><code>email</code></td>
                  <td>string</td>
                  <td><span class="pc-badge pc-badge-opt">optional*</span></td>
                  <td>Valid email if present. Provide <code>phone</code> or <code>email</code> (or both).</td>
                </tr>
                <tr>
                  <td><code>notes</code></td>
                  <td>string</td>
                  <td><span class="pc-badge pc-badge-opt">optional</span></td>
                  <td>Short context for staff. Max 2000 chars.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            Unknown fields (including <code>ssn</code>, addresses, or arbitrary extras) are rejected
            with <span class="pc-status">400</span>.
          </p>

          <h3>Example request</h3>
          <div class="pc-pre-wrap">
            <pre class="pc-pre">{{ curlExample }}</pre>
            <button type="button" class="pc-copy" @click="copyText(curlExample, 'curl')">{{ copyLabel('curl') }}</button>
          </div>

          <h3>Success response</h3>
          <p>
            <span class="pc-status">201 Created</span> on first insert,
            <span class="pc-status">200 OK</span> when the same <code>external_id</code> is posted again.
          </p>
          <div class="pc-pre-wrap">
            <pre class="pc-pre">{{ successExample }}</pre>
          </div>

          <h3>Error responses</h3>
          <div class="pc-table-wrap">
            <table class="pc-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><span class="pc-status">400</span></td>
                  <td>Validation failed or unknown fields present. Body includes <code>errors</code> or <code>unknown</code>.</td>
                </tr>
                <tr>
                  <td><span class="pc-status">401</span></td>
                  <td>Missing, invalid, or inactive API key.</td>
                </tr>
                <tr>
                  <td><span class="pc-status">405</span></td>
                  <td>Method other than <code>POST</code>.</td>
                </tr>
                <tr>
                  <td><span class="pc-status">429</span></td>
                  <td>Rate limit exceeded (default budget: 120 requests / hour / IP).</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section id="idempotency">
          <h2>Idempotency</h2>
          <p>
            Uniqueness is <code>(partner, external_id)</code>. Re-posting the same
            <code>external_id</code> updates name, contact, and notes on the existing referral.
            It does not create a duplicate row.
          </p>
          <p>
            Use your upstream primary key (Airtable record id is ideal) so retries and edits stay safe.
          </p>
        </section>

        <section id="airtable">
          <h2>Airtable / automation notes</h2>
          <ol>
            <li>Trigger on the record status you care about (e.g. “Ready to refer”).</li>
            <li>HTTP request: <code>POST</code> to the endpoint above.</li>
            <li>Header: <code>Authorization: Bearer &lt;your key&gt;</code>.</li>
            <li>JSON body mapped from fields; set <code>external_id</code> to <code>record.id</code>.</li>
          </ol>
          <p>
            Automations run server-side — no browser CORS setup is required for Airtable Scripts,
            Zapier, or Make.
          </p>
        </section>

        <section id="plans">
          <h2>Access tiers</h2>
          <p>Commercial terms live on the contract. Technically:</p>
          <div class="pc-table-wrap">
            <table class="pc-table">
              <thead>
                <tr>
                  <th>Tier</th>
                  <th>API capability</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Mail Slot</strong></td>
                  <td>Write-only <code>POST /api/partners/v1/referrals/</code> as documented here</td>
                  <td>Available</td>
                </tr>
                <tr>
                  <td><strong>Connect+</strong></td>
                  <td>Mail Slot plus optional scoped outbound status fields, gated by release-of-information</td>
                  <td>By arrangement</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            Neither tier grants access to <code>/api/clients/</code> or staff/admin sessions.
          </p>
        </section>

        <section id="support">
          <h2>Support</h2>
          <p>
            For a key, key rotation, or Connect+ scoping, email
            <a :href="mailtoHref">{{ contactEmail }}</a>.
            Include your organization name and the system you will call from (Airtable, Zapier, etc.).
          </p>
        </section>
      </main>
    </div>

    <footer class="pc-footer">
      Mission Hiring Hall · Partner API ·
      <a :href="mailtoHref">{{ contactEmail }}</a>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'

const contactEmail = 'mrobin@missionhiringhall.org'
const mailtoHref =
  'mailto:mrobin@missionhiringhall.org?subject=Partner%20API%20access%20—%20Mission%20Hiring%20Hall'

const baseUrl = 'https://mhh-client-backend-cuambzgeg3dfbphd.centralus-01.azurewebsites.net'
const keyPlaceholder = 'mhh_pk_••••••••'

const toc = [
  { id: 'overview', label: 'Overview' },
  { id: 'base-url', label: 'Base URL' },
  { id: 'auth', label: 'Authentication' },
  { id: 'endpoint', label: 'Endpoint' },
  { id: 'idempotency', label: 'Idempotency' },
  { id: 'airtable', label: 'Airtable' },
  { id: 'plans', label: 'Access tiers' },
  { id: 'support', label: 'Support' },
] as const

const activeSection = ref<string>('overview')
const copiedKey = ref('')

const curlExample = computed(
  () => `curl -X POST '${baseUrl}/api/partners/v1/referrals/' \\
  -H 'Authorization: Bearer ${keyPlaceholder}' \\
  -H 'Content-Type: application/json' \\
  -d '{
    "external_id": "recXXXXXXXX",
    "first_name": "Jordan",
    "last_name": "Lee",
    "phone": "4155551212",
    "email": "jordan@example.org",
    "notes": "Interested in orientation next week"
  }'`,
)

const successExample = `{
  "id": 42,
  "external_id": "recXXXXXXXX",
  "status": "pending",
  "created": true,
  "message": "Referral received for staff review."
}`

function copyLabel(key: string) {
  return copiedKey.value === key ? 'Copied' : 'Copy'
}

async function copyText(text: string, key?: string) {
  try {
    await navigator.clipboard.writeText(text)
    copiedKey.value = key || text
    window.setTimeout(() => {
      if (copiedKey.value === (key || text)) copiedKey.value = ''
    }, 1600)
  } catch {
    /* ignore */
  }
}

let observer: IntersectionObserver | null = null

onMounted(() => {
  const sections = toc.map((t) => document.getElementById(t.id)).filter(Boolean) as HTMLElement[]
  observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((e) => e.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
      if (visible[0]?.target?.id) {
        activeSection.value = visible[0].target.id
      }
    },
    { rootMargin: '-20% 0px -55% 0px', threshold: [0.1, 0.4, 0.7] },
  )
  for (const el of sections) observer.observe(el)
})

onUnmounted(() => observer?.disconnect())
</script>
