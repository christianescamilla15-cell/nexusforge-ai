# NexusForge Showcase — Demo Script

**Target length**: 4-6 minute video
**Audience**: potential clients, stakeholders, hiring managers
**URL to open**: `https://07-nexusforge-ai.vercel.app/showcase`

This script is designed for a screen-recorded walkthrough (Loom, OBS,
or similar) of the `/showcase` page. It pairs narration beats with
specific UI pointers and the core "weeks not years" narrative. Each
section is timed and the numbers you read aloud match the live
`tenant-alpha` data so the demo stays honest.

---

## Pre-recording checklist (30 seconds before you hit record)

- [ ] Open `https://07-nexusforge-ai.vercel.app/showcase` in a clean browser window (incognito is fine, no extensions)
- [ ] Zoom in to **110-125%** so the hero band and cards are legible on 1080p
- [ ] Close all other tabs — viewers will read the tab strip
- [ ] Disable system notifications (macOS: Focus mode / Windows: Focus assist)
- [ ] Have a second tab ready with the **Executive Report Out modal** pre-opened (click "View Executive Report Out" once, close it, reopen on camera)
- [ ] Make sure your mic is the good one
- [ ] One dry run WITHOUT recording — the first take is always the worst

---

## 0:00 – 0:15 · Opening hook

**[Camera on hero band, specifically on the "5 apps / 23K LOC / 3,855 findings / 0.72s" stat row]**

> "Legacy modernization usually takes months. You get a fat assessment
> deck, a six-week discovery, and then another three months of handoffs
> before anyone writes a single line of code. What you're looking at
> right now — five applications, twenty-three thousand lines of code,
> almost four thousand vulnerabilities detected — NexusForge produced
> in zero point seven two seconds."

**[Hold on the "0.72s" number for a beat, then continue]**

> "Let me show you what's actually in there."

---

## 0:15 – 0:45 · The showcase in one screen

**[Scroll slowly top to bottom of the hero band and the action bar]**

> "This is the tenant-alpha showcase — it's a synthetic enterprise
> built to match the structural profile of a real modernization
> program. Five applications, each with its own tech debt story: C#
> ASP.NET on top of a legacy MySQL, a .NET batch sales system, a
> Python RPA robot wrapping refunds, a document ingestion pipeline,
> and at the core a commission engine that still runs COBOL on the
> mainframe."

**[Cursor on the "View Executive Report Out" button but don't click yet]**

> "Everything you're about to see — the migration plan, the compliance
> posture, the commercial risk, the governance structure — NexusForge
> generates automatically from a single pass over the codebase."

---

## 0:45 – 1:30 · Compliance countdown

**[Scroll to ComplianceCard]**

> "First, the hard deadline. This tenant has a September 30, 2026
> go-live commitment driven by three certifications: Sarbanes-Oxley
> Section 404 for financial controls, SOC 2 Type II for operations,
> and a generic data privacy regulation that lit up after a prior
> incident."

**[Point to the countdown number, then to the at-risk banner if visible]**

> "NexusForge counts the days to the deadline, colors them green,
> amber or red, and flags any certification that's at risk. The
> timeline below shows the four program phases — discovery,
> execution, testing, and production cutover — and which one we're
> in right now based on today's date."

**[Hover over one of the phase cards to show the milestones]**

> "Each phase carries its own milestones, so the project manager sees
> exactly which work blocks the hard deadline."

---

## 1:30 – 2:15 · Commercial risk

**[Scroll to CommercialRiskCard]**

> "Legacy modernization programs don't die from tech debt — they die
> from vendor lock-in and contract drift. NexusForge surfaces that as
> its own layer."

**[Point to the $18.5M and 40% numbers]**

> "Total worst-case penalty exposure: eighteen point five million
> dollars across three categories — reputational, privacy and data
> integrity. And this is the one that catches people off guard: forty
> percent of vendor spend is running without a written contract. Your
> CFO needs to know that number."

**[Point to the vendor rows]**

> "Three vendors: the legacy platform vendor with a high lock-in
> level and sixty percent of their total revenue coming from this
> client, the cloud hyperscaler running ninety percent of the
> workloads, and a consulting partner on short-term engagements.
> NexusForge captures the revenue share, two-year spend, contract
> coverage and lock-in level for each."

**[Point to the penalty bars]**

> "The bars at the bottom are proportional to the total exposure.
> Reputational risk dominates — thirteen million of the eighteen-
> five total."

---

## 2:15 – 3:00 · Governance

**[Scroll to GovernanceCard]**

> "Governance is the non-technical layer that actually determines
> whether a program ships. NexusForge captures four things here."

**[Point to each sub-section as you describe]**

> "First, the steering committee: monthly on the fourteenth, chaired
> by the program manager, with six generic attendee roles — compliance,
> CISO, CFO delegate, architecture lead, legacy vendor liaison."

> "Second, delivery teams: three teams running in parallel. Team
> primary owns the five scoped apps. Team secondary handles apps
> outside this tenant. Team core — the legacy vendor's team — handles
> the mainframe workstream. That's the strangler-pattern split in
> real life."

**[Point to the red code-access card]**

> "Third, code access. This one's flagged as a bottleneck — see the
> red border and the bottleneck badge? The legacy vendor controls an
> intermediate reviewer on all code changes. That's not a security
> control, it's a delivery bottleneck. NexusForge makes it visible
> so stakeholders can decide whether to negotiate a direct path."

> "Fourth, the post-launch tech lead slot. Recruiting, with a target
> start date of June 2026. This is the role that owns knowledge
> transfer from the external delivery teams to the internal
> organization."

---

## 3:00 – 3:45 · App list + strangler plans

**[Scroll to the app list on the left]**

> "Now the applications themselves. Each card shows the codename,
> label, file count, LOC, weighted risk score and total findings.
> The colored pill is the pre-assigned refactor decision — refactor,
> retire, retain or TBD — with the phase it belongs to."

**[Click on app-05]**

> "App-05 is the nexus — the commission engine. Highest LOC, most
> findings, most complex. NexusForge classifies it as a REFACTOR in
> Phase 2."

**[Point to the strangler plan on the right]**

> "And here's the strangler plan for it. Five phases, low risk at
> the edges, high risk at the shared libraries and the mainframe
> core. Phase one extracts the outer controllers — that's what you
> do first to get a gateway in front of the legacy. Phase five wraps
> the COBOL. Never rewrites it."

**[Click on app-03]**

> "App-03 is different. It's marked as TBD slash IMMEDIATE because
> the database has been inactive since March 2023 — over two and a
> half years of zero transactions. See that red warning strip? That
> means this app is a retirement candidate, but NexusForge requires
> dual validation before decommissioning: the team has to confirm
> that the exploits are not actually reachable AND that no business
> process still depends on it."

---

## 3:45 – 4:30 · The Report Out modal (climax)

**[Click "View Executive Report Out"]**

> "Last piece. Everything I just showed you — compliance, commercial
> risk, governance, per-app breakdown, strangler plans — NexusForge
> assembles into a single markdown document. This is the
> stakeholder-facing Report Out. You hand this to your CFO, your
> CISO, your board, and they read it without having to click
> through a dashboard."

**[Scroll through the modal]**

> "Seven sections: executive summary with the critical numbers, per-
> app breakdown table, strangler migration plan summary with total
> engineer-days, commercial risk with vendor dependencies, governance
> with the code access bottleneck flagged, compliance countdown with
> all three certifications, and a 'next thirty days' actionable list
> that your PM can paste directly into a sprint."

**[Point to the Download button]**

> "One click to download the whole thing as a markdown file. Paste
> into Confluence, email to a sponsor, commit to a repo — all of it
> works."

---

## 4:30 – 5:00 · The value prop close

**[Close the modal, scroll to the dark narrative footer]**

> "So here's the pitch. Traditional modernization discovery takes
> three to six months and costs hundreds of thousands of dollars in
> consulting fees before anyone commits code. NexusForge did the
> same work on five applications, including the strangler plan, the
> compliance mapping, the commercial risk layer and the governance
> metadata, in under a second."

**[Hover over "0.72s" in the hero band]**

> "The number you see up there is real. Every time someone opens
> this page, the pipeline is either reading from a persisted
> PostgreSQL snapshot or falling back to static JSON fixtures —
> which means the demo is always reproducible. No cherry-picked
> runs. No staged screenshots."

**[Scroll to the bottom]**

> "Manual discovery: months. With NexusForge: seconds. That's the
> pitch."

---

## 5:00 – 5:30 · Technical depth (optional B-roll)

**If the audience is technical, add this section. Otherwise cut here.**

**[Open DevTools Network tab, click refresh on /showcase]**

> "Under the hood, the page fetches five endpoints in parallel:
> /showcase for the per-app summary, /compliance for the countdown,
> /commercial-risk for vendors and penalties, /governance for the
> org structure, and /strangler per-app for the migration plan.
> All of them are public — no auth needed — because the showcase is
> a demo surface."

**[Close DevTools]**

> "The backend is FastAPI on Render. The frontend is React 18 plus
> Vite on Vercel. The data is generated by a deterministic seeded
> synthesizer that matches the structural profile of real
> enterprise programs — five point six million lines of code, thirty
> one applications, three thousand SQL injections, twenty five types
> of personal data. I can spin up a new tenant in thirty seconds
> with different parameters if a client asks."

---

## 5:30 – 5:45 · Outro + call to action

**[Back to hero band, zoom slightly out so the full page is visible]**

> "If you're dealing with a legacy modernization program and the
> discovery phase is eating your timeline, I'd love to show you how
> this compresses to days. The URL is on screen, and if you want to
> talk, [YOUR CONTACT]. Thanks for watching."

---

## Narration anti-patterns to avoid

- **Don't** say "and as you can see here" — the viewer already sees it
- **Don't** apologize ("sorry for the rough demo") — it makes everything feel unfinished
- **Don't** read the UI labels verbatim — paraphrase
- **Don't** mention specific real client names, sectors or geographies (confidentiality rule)
- **Don't** promise features that aren't live on the `/showcase` page
- **Don't** compare against named competitors ("unlike X") — invites lawsuits

## Confidentiality rules for this demo

- No real client names or identifiers from any engagement appear in the showcase UI
- No sector-specific terminology that could identify a client industry
- No specific people names, roles tied to real individuals, or geographies
- The word "generic" or "synthetic" is your friend — lean on it when describing the data

If a viewer asks "what industry is this for?" your answer is:

> "Any industry with legacy enterprise systems — financial services,
> insurance, healthcare, transportation, utilities. The structural
> profile is the same: 20+ applications, multiple languages, a
> mainframe core, a vendor relationship that's gone sideways, and a
> compliance deadline that's not moving."

## Re-takes

The demo runs about 5-6 minutes. Most re-takes happen in two places:

1. **The hero intro** — getting the "zero point seven two seconds"
   beat to land. Practice that line three times before recording.
2. **The Report Out modal scroll** — the modal has a lot of content,
   easy to scroll too fast. Move the cursor slowly and read one or
   two lines from each section aloud as you pass them.

If you fluff a line, cut on a scroll (scrolling covers the edit
naturally). Don't try to do the whole demo in one take — cut between
sections.

---

_Last updated: 2026-04-10 by the NexusForge showcase team._
