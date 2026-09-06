export const meta = {
  name: 'securemed-ui-audit',
  description: 'Audit SecureMed web + Android UI (design system, motion, imagery, a11y/RTL, parity, perf) and verify every cited finding',
  phases: [
    { title: 'Audit', detail: '10 dimension auditors read frontend/src and android Compose UI in parallel' },
    { title: 'Verify', detail: '3 skeptics re-read every cited line and drop unsupported findings' },
    { title: 'Gaps', detail: 'completeness critic names UI surface nobody covered' },
  ],
}

const ROOT = 'c:/Users/Essa/Downloads/securemed'

const GROUND_RULES = [
  'You are auditing the UI of the SecureMed project. Repository root: ' + ROOT,
  '',
  'There are exactly TWO UI surfaces:',
  '  WEB     -> ' + ROOT + '/frontend',
  '            React 18 + TypeScript + Vite + Tailwind 3 (darkMode class) + framer-motion 13 + Radix UI',
  '            + lucide-react + recharts + react-hot-toast + zustand + @tanstack/react-query.',
  '            30 pages in src/pages/ (16,455 LOC across src), shared bits in src/components/common and /fx.',
  '            Arabic RTL UI: index.css sets direction:rtl on body; all user-facing copy is Arabic.',
  '  ANDROID -> ' + ROOT + '/android/app/src/main',
  '            Jetpack Compose + Material3 + Hilt + Room/SQLCipher + Retrofit + Coil.',
  '            22 screens in java/com/securemed/app/ui/screens/ (6,322 LOC), theme in ui/theme/,',
  '            shared bits in ui/components/, resources in res/.',
  '',
  'NEVER read, count or cite anything under: SecureMed-main/ (stale unzipped duplicate of the whole repo),',
  'frontend/node_modules/, frontend/dist/ (except for chunk sizes if asked), backend/venv/, backend/.venv/,',
  'backend/staticfiles/, backend_obfuscated/, .git/. Findings citing those paths are invalid.',
  '',
  'HARD RULES',
  '1. Every finding MUST carry evidence as repo-relative path:line (forward slashes), e.g.',
  '   "frontend/src/pages/Dashboard.tsx:201, frontend/src/index.css:52". No citation -> do not report it.',
  '2. Report only what you actually read. Never speculate about runtime behaviour you did not see in code.',
  '3. Prefer counted facts over adjectives. "24 of 30 pages hand-roll their own header instead of importing',
  '   common/PageHeader" beats "headers are inconsistent".',
  '4. Also record what ALREADY WORKS and must not be regressed, in keep[].',
  '5. The goal driving this audit (the user asked in Arabic): make the interfaces professional and',
  '   interactive, rich with imagery, UNIFIED across the product, with real animation and interaction.',
  '   Judge everything against that goal.',
  '6. Write findings in English. The final plan is translated to Arabic separately.',
  '',
  'Baseline facts already established - rely on them, re-verify only what you cite:',
  '  - frontend/src/components/common/Card.tsx is imported by 6 files, while 13 pages use the raw .card CSS',
  '    class from index.css (59 occurrences) - and the two render differently.',
  '  - common/PageHeader imported by 6 files; common/Modal by 7; common/AnimatedPage by 0;',
  '    fx/FloatingParticles by 0; fx/PageTransition by 1; fx/CountUp by 1; fx/ECGLine by 3;',
  '    fx/AnimatedBackground by 2.',
  '  - .skeleton exists in index.css but has 0 uses in src/pages; 10 pages use ad-hoc animate-pulse.',
  '  - Only 2 of the 4 files in frontend/public/images/ are referenced (login-hero.jpg at',
  '    pages/Login.tsx:531, team.jpg at pages/Dashboard.tsx:201). care.jpg and lab.jpg are unused.',
  '  - The <img tag is used 5 times total across all 30 pages. aria-label appears in 3 files (4 uses);',
  '    role= has 0 uses in src/pages.',
  '  - android res/ holds only: drawable/ic_medication.xml, launcher mipmaps, values/colors.xml,',
  '    values/strings.xml, values/themes.xml, values-ar/strings.xml (15 strings each),',
  '    xml/data_extraction_rules.xml, xml/network_security_config.xml. There is no values-night/,',
  '    no dimens.xml, no font/, no anim/, no image assets and no assets/ directory.',
].join('\n')

const FINDING = {
  type: 'object',
  properties: {
    title: { type: 'string', description: 'One specific line. Name the artifact.' },
    evidence: { type: 'string', description: 'repo-relative path:line citations, comma separated' },
    impact: { type: 'string', description: 'What a user of the app actually sees or feels because of this' },
    severity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low'] },
    fix: { type: 'string', description: 'Concrete remedy: files to add/change, component names, token names' },
    effort: { type: 'string', enum: ['S', 'M', 'L', 'XL'] },
    platform: { type: 'string', enum: ['web', 'android', 'both'] },
  },
  required: ['title', 'evidence', 'impact', 'severity', 'fix', 'effort', 'platform'],
}

const AUDIT_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    summary: { type: 'string', description: '3-6 sentences: the state of this dimension today' },
    metrics: { type: 'array', items: { type: 'string' }, description: 'Countable facts with citations' },
    keep: { type: 'array', items: { type: 'string' }, description: 'What already works well; do not regress' },
    findings: { type: 'array', items: FINDING },
  },
  required: ['dimension', 'summary', 'findings'],
}

const VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string' },
          supported: { type: 'boolean' },
          note: { type: 'string', description: 'Why it holds, or exactly what the cited line really says' },
          correctedEvidence: { type: 'string' },
          correctedSeverity: { type: 'string', enum: ['blocker', 'high', 'medium', 'low', ''] },
        },
        required: ['id', 'supported', 'note'],
      },
    },
  },
  required: ['verdicts'],
}
const DIMENSIONS = [
  {
    key: 'tokens',
    prompt: [
      'DIMENSION: design tokens, theming and single-source-of-truth.',
      'Read: frontend/tailwind.config.js, frontend/src/index.css, frontend/src/store/themeStore.ts,',
      'frontend/index.html, frontend/src/main.tsx, frontend/src/App.tsx,',
      'android/app/src/main/java/com/securemed/app/ui/theme/Theme.kt and Typography.kt,',
      'android/app/src/main/res/values/colors.xml and values/themes.xml.',
      'Answer with evidence: Where do colour/spacing/radius/shadow/duration values live? How many separate',
      'places define the SAME brand colour (tailwind primary-600 vs res/values/colors.xml vs Theme.kt)? Are',
      'there hardcoded hex/rgba literals inside page and screen files that bypass the tokens - count them',
      'and cite the worst offenders. Is dark mode complete on web (audit the dark: variants - which',
      'components have no dark treatment)? Where is the dark class applied, and can a page paint in the',
      'wrong theme on first load before that effect runs (FOUC)? Is there any SEMANTIC token layer',
      '(surface / surface-muted / border / text-muted / danger) or only raw palette scales? Are the fonts',
      '(Inter / Cairo / Noto Sans Arabic) self-hosted or fetched from the Google Fonts CDN at runtime, and',
      'what does that mean for a medical app behind a CSP - grep backend/config/settings*.py for CSP or',
      'Content-Security-Policy and say whether fonts.googleapis.com would be blocked. Is there any',
      'radius/spacing/elevation scale at all, or per-component guesses - count the distinct rounded-*',
      'values used across src/pages.',
    ].join('\n'),
  },
  {
    key: 'components',
    prompt: [
      'DIMENSION: shared component library, duplication and drift on WEB.',
      'Read every file in frontend/src/components/ (common/, fx/, and the feature modal folders',
      'appointments/, billing/, lab/, pharmacy/, telemedicine/), then sample at least 12 of the 30 files in',
      'frontend/src/pages/ - including the largest (PatientProfile 1281, Telemedicine 799, SettingsPage 783,',
      'PharmacyDashboard 709, Dashboard 640, Login 603, DeviceManagement 574, ChannelDetail 564) and several',
      'small ones for contrast.',
      'Answer with evidence: Build the duplication table. For each recurring UI concept - page header,',
      'stat/KPI tile, card, table or list row, badge/status pill, empty state, filter bar, search input,',
      'modal, tab bar, avatar, button variants, pagination - state whether a shared component exists, how',
      'many pages import it, and how many pages reimplement it inline. Quote the diverging markup for at',
      'least 3 concepts so the drift is provable (e.g. Card.tsx own classes vs the .card class in',
      'index.css - do they produce the same surface in light and in dark?). Identify dead code (exported',
      'components with zero importers). Identify the 5 pages that would change the most under a unified',
      'component library. Is there any barrel/index export, any variant API (cva or clsx patterns), any',
      'shared TypeScript prop contract across components?',
    ].join('\n'),
  },
  {
    key: 'motion',
    prompt: [
      'DIMENSION: animation and micro-interaction system on WEB.',
      'Read frontend/tailwind.config.js (the animation and keyframes blocks), frontend/src/index.css,',
      'frontend/src/components/fx/*.tsx, frontend/src/components/common/AnimatedPage.tsx,',
      'frontend/src/components/Layout.tsx, and grep for motion. / AnimatePresence / whileHover / whileTap /',
      'layoutId / transition= across frontend/src to map actual usage (102 motion. occurrences in 11 page',
      'files).',
      'Answer with evidence: How many DISTINCT animation durations and easing curves are in use? List them',
      'with citations - that number IS the finding. Which motion primitives are defined but unused (dead),',
      'and which pages animate with inline one-off values instead? Layout.tsx runs its own inline route',
      'transition while fx/PageTransition.tsx exports a different one - give both specs and say which one',
      'actually renders. Does anything respect prefers-reduced-motion in JavaScript? Note precisely:',
      'index.css has a prefers-reduced-motion media block that overrides CSS animation-duration and',
      'transition-duration, but framer-motion drives transforms and opacity via inline style from JS.',
      'Confirm whether useReducedMotion or MotionConfig appears anywhere in frontend/src, and state the',
      'consequence for a user with vestibular sensitivity. Audit the global star rule in index.css that',
      'sets transition-property to background-color and border-color with a 200ms duration on EVERY',
      'element - which interactions does that unintentionally slow or fight? Which high-value interactions',
      'have NO feedback at all (button press, row click, successful save, list reorder, tab change, drag,',
      'hover on chart, skeleton-to-content handoff)? Is any stagger applied to the lists and card grids on',
      'pages that show many items?',
    ].join('\n'),
  },
  {
    key: 'imagery',
    prompt: [
      'DIMENSION: imagery, iconography, avatars and illustration - BOTH platforms.',
      'Read frontend/public/ (all of it), frontend/src/pages/Login.tsx and Dashboard.tsx around the two img',
      'uses, grep frontend/src for the img tag, background-image, backgroundImage, url(, Avatar, avatar,',
      'initials, placeholder; and on Android grep for coil, AsyncImage, rememberAsyncImagePainter,',
      'painterResource, Icons. and ImageVector across android/app/src/main/java.',
      'Answer with evidence: Inventory every raster and vector asset that exists and its byte size (ls -l',
      'or stat). Which are unused? Are images served in a modern format (webp/avif) or plain jpg, and are',
      'they responsive (srcset/sizes) or one fixed file? Is there ANY image component wrapping loading',
      'state, blur-up/LQIP, aspect-ratio reservation against layout shift, error fallback, loading=lazy,',
      'or alt text? Check the alt text on every img that exists. How are user avatars rendered - is it',
      'always a text initial in a gradient circle, and is there any real photo/upload path (grep',
      'backend/apps/*/models.py for avatar, photo, image, ImageField)? Is there any empty-state',
      'illustration, onboarding art, or medical iconography beyond the lucide and Material icon fonts?',
      'Android: coil-compose is a declared dependency - is a single AsyncImage actually used anywhere?',
      'res/ has exactly one vector drawable (ic_medication.xml) - so what do the 22 screens draw when they',
      'need art? Do the two platforms share ANY visual asset (logo, launcher, hero) or is the branding',
      'drawn twice in code?',
    ].join('\n'),
  },
  {
    key: 'android-ui',
    prompt: [
      'DIMENSION: the Android Compose UI itself.',
      'Read android/app/src/main/java/com/securemed/app/ui/theme/Theme.kt and Typography.kt,',
      'ui/MainActivity.kt, ui/components/StateLayout.kt, PullToRefreshLayout.kt, ShimmerEffect.kt,',
      'BottomNavBar.kt, navigation/Routes.kt, and at least 8 screens including the largest',
      '(MedicationsScreen 610, ProfileScreen 465, DashboardScreen 429, SettingsScreen 405, UsersScreen 377,',
      'LoginScreen 375, TwoFactorScreen 276, ChannelDetailScreen 269) plus res/values/themes.xml,',
      'res/values/strings.xml, res/values-ar/strings.xml and app/src/main/AndroidManifest.xml.',
      'Answer with evidence: Is there a dark colour scheme, and is it reachable by the user (a theme',
      'toggle? follows the system? any values-night?)? Is dynamic color used or a fixed brand scheme? Is',
      'the Material3 typography scale customised for Arabic - is an Arabic-capable font bundled at all, or',
      'does it fall back to the system font? Theme.SecureMed parents android:Theme.Material.Light.NoActionBar',
      'with a hardcoded statusBarColor - what breaks (edge-to-edge, status-bar contrast in dark mode,',
      'Material3 attribute inheritance, predictive back)? LOCALISATION: strings.xml holds 15 strings while',
      'the screens total 6,322 lines - count the hardcoded user-facing string literals in the Kotlin screens,',
      'cite examples, and say what that means for values-ar. Are the shared components actually used across',
      'screens (count importers of StateLayout, ShimmerEffect, PullToRefreshLayout)? Do screens hardcode',
      'Color(0xFF...) and raw dp instead of MaterialTheme.colorScheme and a spacing scale - count and cite.',
      'Which screens have no loading/empty/error handling? Is there ANY animation on Android',
      '(AnimatedVisibility, animate*AsState, Crossfade, navigation transitions) - count occurrences. Is the',
      'bottom nav IA consistent with the web sidebar? Are there Compose @Preview functions, and any UI',
      'tests under app/src/androidTest?',
    ].join('\n'),
  },
  {
    key: 'parity',
    prompt: [
      'DIMENSION: cross-platform parity and information architecture.',
      'Read frontend/src/App.tsx (the route table), frontend/src/components/Layout.tsx (the navItems array),',
      'frontend/src/constants/roles.ts, android/app/src/main/java/com/securemed/app/navigation/Routes.kt,',
      'android/app/src/main/java/com/securemed/app/ui/MainActivity.kt (the NavHost) and',
      'android/app/src/main/java/com/securemed/app/ui/components/BottomNavBar.kt, plus the file listings of',
      'frontend/src/pages/ and android/app/src/main/java/com/securemed/app/ui/screens/.',
      'Answer with evidence: Produce the parity matrix - for each product area (dashboard, channels,',
      'patients, appointments, telemedicine, analytics, reports, security dashboard, devices, login history,',
      'security settings, audit logs, users, pharmacy, billing, lab, wards, basins, backups, notifications,',
      'profile, settings, 2FA, lock screen, forgot-password) say whether it exists on web, on Android, on',
      'both, or neither, with the file that proves it. Count the gaps in each direction. Where an area',
      'exists on both, do they present the same information hierarchy and the same primary action, or has',
      'each platform invented its own layout? Is navigation role-gated identically on both (web filters',
      'navItems by role - does Android)? Which naming is inconsistent between platforms for the same',
      'concept? What is the single biggest IA divergence a user switching device would notice?',
    ].join('\n'),
  },
  {
    key: 'a11y-rtl',
    prompt: [
      'DIMENSION: accessibility, RTL correctness and Arabic typography - BOTH platforms.',
      'Read frontend/src/index.css, frontend/index.html, frontend/src/components/Layout.tsx,',
      'GlobalSearch.tsx, AIAssistant.tsx, ErrorBoundary.tsx, frontend/src/components/common/Modal.tsx, at',
      'least 6 pages with forms/tables/modals (Login, SettingsPage, Users, Patients, Appointments,',
      'SecuritySettings), and on Android the theme, the manifest and 4 screens.',
      'Answer with evidence: RTL - is direction handled with logical CSS properties (start/end, ms-/me-/',
      'ps-/pe-) or with physical right/left? Count physical-direction utilities (right-, left-, ml-, mr-,',
      'pl-, pr-, text-left, text-right) across src/pages and name the pages where that mirrors wrongly;',
      'note that Tailwind 3 does NOT auto-flip physical utilities. Are gradients, icons, chevrons and',
      'progress directions mirrored for RTL (bg-gradient-to-l is used - is that intentional everywhere)?',
      'A11Y - with aria-label at 4 uses and role= at 0 uses across 30 pages: which interactive elements are',
      'icon-only buttons with no accessible name - count and cite. Are modals focus-trapped,',
      'Escape-closable, aria-modal, and do they restore focus? Check common/Modal.tsx against the Radix',
      'dialogs - are BOTH patterns in use, and do they behave differently? Is there a visible focus ring, or',
      'does any reset remove outlines? Is there a skip-to-content link? Do form fields have label-for',
      'associations, and is error text linked via aria-describedby or role=alert? Are toasts announced',
      '(react-hot-toast is not a screen-reader live region unless configured)? CONTRAST: take at least 4',
      'real colour pairs found in the code (e.g. text-gray-400 on white, text-gray-500 on gray-50,',
      'white on the primary gradient button, text-gray-400 on gray-800 in dark mode), compute the actual',
      'WCAG ratio for each, and say pass or fail against 4.5:1. Android: are contentDescription set on',
      'icons, are touch targets at least 48dp, and is android:supportsRtl declared in the manifest?',
    ].join('\n'),
  },
  {
    key: 'states',
    prompt: [
      'DIMENSION: interaction states and data-entry UX on WEB - loading, empty, error, success, forms, tables.',
      'Read frontend/src/api/client.ts, frontend/src/hooks/useRealtimeNotifications.ts,',
      'frontend/src/components/ErrorBoundary.tsx, frontend/src/components/common/Modal.tsx, and at least 10',
      'pages that fetch lists or submit forms (Patients, Users, Appointments, AuditLogs, LoginHistory,',
      'NotificationsCenter, PharmacyDashboard, LabDashboard, BillingDashboard, WardManagement) plus 3 of the',
      'feature modals.',
      'Answer with evidence: For each page you read, tabulate which of the four states it renders - loading,',
      'empty, error, success - and how (spinner? animate-pulse? nothing? a toast?). Count how many distinct',
      'loading treatments exist across the app and cite each. Is isLoading/isError from react-query handled',
      'or silently ignored? Are mutations optimistic, and is there a pending/disabled state on submit',
      'buttons - count buttons that can be double-submitted. Are destructive actions confirmed, and by what',
      '- window.confirm or a styled dialog (grep for confirm()) ? Do lists have pagination, sorting and',
      'filtering, and is that state reflected in the URL so a view is shareable and back-button-safe? Do',
      'forms validate inline or only on submit, is any validation library used, and where does server error',
      'detail surface? Are toasts the only error channel - what happens when a request fails while the tab',
      'is backgrounded? Is there any skeleton shaped like the content it replaces (layout-stable) rather',
      'than a centred spinner?',
    ].join('\n'),
  },
  {
    key: 'dataviz',
    prompt: [
      'DIMENSION: charts and analytics presentation on WEB.',
      'Read frontend/src/pages/Analytics.tsx, AnalyticsDashboard.tsx, Dashboard.tsx, SecurityDashboard.tsx,',
      'Reports.tsx, BillingDashboard.tsx, LabDashboard.tsx, PharmacyDashboard.tsx and',
      'frontend/src/components/fx/CountUp.tsx and ECGLine.tsx; grep frontend/src for recharts,',
      'ResponsiveContainer, LineChart, BarChart, PieChart, AreaChart, Cell, fill= and stroke=.',
      'Answer with evidence: Inventory every chart - page, chart type, what it encodes, and the exact',
      'colours it uses. Are chart colours drawn from the design tokens or hardcoded hex per chart? List',
      'every distinct hex found in chart props with citations. Is there a single categorical palette, or',
      'does each chart pick its own series colours - and do any two adjacent series differ only in',
      'lightness? Are charts legible in dark mode (axis, tick, grid and tooltip colours - are they',
      'hardcoded light-mode greys)? Is there a shared chart wrapper (title, subtitle, legend, empty state,',
      'loading state, aspect ratio, no-data message) or is every ResponsiveContainer configured from',
      'scratch? Do charts have any accessible fallback (a table alternative, aria, or is it a bare SVG)?',
      'Are number and date formats localised for Arabic - are Arabic-Indic vs Western digits consistent, is',
      'date-fns given an ar locale? Are KPI tiles animated with CountUp consistently (CountUp has 1',
      'importer - which KPI numbers just snap in)? Do any two pages show the same metric with different',
      'formatting, or use the same colour with opposite meaning (red = good on one page, bad on another)?',
    ].join('\n'),
  },
  {
    key: 'perf',
    prompt: [
      'DIMENSION: UI performance and delivery.',
      'Read frontend/vite.config.ts, frontend/src/App.tsx (route definitions - is React.lazy used?),',
      'frontend/src/main.tsx, frontend/package.json, frontend/src/components/Layout.tsx (polling intervals),',
      'frontend/src/components/fx/*.tsx (are the decorative animations cheap?), and list the built output if',
      'it exists (ls -l frontend/dist/assets). Also stat the files in frontend/public/images.',
      'Answer with evidence: Are routes code-split with React.lazy and Suspense, or is every one of the 30',
      'pages in the entry bundle? What are the actual built chunk sizes if dist/ exists? Which heavy',
      'dependencies land in the main chunk (recharts, framer-motion, lucide-react - is lucide imported',
      'per-icon or barrel-imported)? Is there any manualChunks config? IMAGE WEIGHT: total bytes of',
      'public/images and the largest single file - what does that cost on a hospital 3G connection?',
      'ANIMATION COST: which decorative effects animate non-composited properties (borderRadius in the blob',
      'keyframes, filter in glow, backgroundPosition in shimmer and gradient) and how many run',
      'simultaneously and forever on a page - cite the keyframes and the components that mount them. Does',
      'the global star transition rule in index.css force style recalculation on every element? POLLING:',
      'Layout.tsx refetches the unread count every 20s - inventory every refetchInterval and setInterval in',
      'src and its cost. Any obvious re-render hazards (store subscriptions that rerender the whole tree,',
      'non-memoised heavy lists, key={index})? Is there a font-display strategy, and does the Google Fonts',
      'request block first paint?',
    ].join('\n'),
  },
]
phase('Audit')
log('10 dimension auditors reading frontend/src (16.5k LOC) and android Compose UI (6.3k LOC)')
const audits = (await parallel(DIMENSIONS.map(function (d) {
  return function () {
    return agent(GROUND_RULES + '\n\n' + d.prompt, {
      label: 'audit:' + d.key,
      phase: 'Audit',
      schema: AUDIT_SCHEMA,
    })
  }
}))).filter(Boolean)

// Barrier is deliberate: the verification slices and the gap critic both need the FULL finding set.
const allFindings = []
audits.forEach(function (a, ai) {
  const key = DIMENSIONS[ai] ? DIMENSIONS[ai].key : 'dim' + ai
  const fs = a.findings || []
  fs.forEach(function (f, fi) {
    allFindings.push(Object.assign({}, f, { id: key + '#' + fi, dim: key }))
  })
})
log(allFindings.length + ' findings from ' + audits.length + ' auditors; verifying every citation')

phase('Verify')
const SLICES = 3
const slices = []
for (let s = 0; s < SLICES; s++) {
  slices.push(allFindings.filter(function (_, i) { return i % SLICES === s }))
}
const verifyRuns = (await parallel(slices.map(function (slice, s) {
  return function () {
    return agent(
      GROUND_RULES +
        '\n\nDIMENSION: adversarial verification. Below are ' + slice.length + ' findings from other ' +
        'auditors. Your job is to REFUTE them. For each one: open the cited path:line yourself and read ' +
        'it. Then set supported=true only if the cited code genuinely demonstrates the claim AND the claim ' +
        'is materially true of the codebase - not a nitpick dressed up as a defect, not something already ' +
        'handled elsewhere in a file the auditor did not open, not a wrong count. Default to ' +
        'supported=false when the citation is wrong, the line does not say what is claimed, the count is ' +
        'off, or the so-called problem is actually correct practice. If the claim is true but the severity ' +
        'is inflated or deflated, set supported=true and give correctedSeverity. If the evidence is weak ' +
        'but a better citation exists, set correctedEvidence. Return one verdict per id - all ' +
        slice.length + ' of them, no omissions.\n\nFINDINGS:\n' + JSON.stringify(slice, null, 1),
      { label: 'verify:slice' + (s + 1), phase: 'Verify', schema: VERIFY_SCHEMA, effort: 'high' }
    )
  }
}))).filter(Boolean)
const verdictById = {}
verifyRuns.forEach(function (r) {
  (r.verdicts || []).forEach(function (v) { verdictById[v.id] = v })
})
const merged = allFindings.map(function (f) {
  const v = verdictById[f.id]
  return Object.assign({}, f, {
    supported: v ? v.supported : null,
    verifyNote: v ? v.note : 'NOT VERIFIED - no verdict returned',
    evidence: v && v.correctedEvidence ? v.correctedEvidence : f.evidence,
    severity: v && v.correctedSeverity ? v.correctedSeverity : f.severity,
  })
})
const confirmed = merged.filter(function (f) { return f.supported === true })
const refuted = merged.filter(function (f) { return f.supported === false })
const unverified = merged.filter(function (f) { return f.supported === null })
log('verified: ' + confirmed.length + ' confirmed, ' + refuted.length + ' refuted, ' + unverified.length + ' unverified')

phase('Gaps')
const critic = await agent(
  GROUND_RULES +
    '\n\nDIMENSION: completeness critic. Ten auditors covered these dimensions: ' +
    DIMENSIONS.map(function (d) { return d.key }).join(', ') + '. Their confirmed findings are listed below.\n\n' +
    'Your job: name what is MISSING from this audit, judged against the goal of a professional, unified, ' +
    'image-rich, animated, interactive product across web and Android. Specifically hunt for: ' +
    '(a) UI surface nobody opened - list the files in frontend/src/pages, frontend/src/components and ' +
    'android/app/src/main/java/com/securemed/app/ui that appear in NO citation below, then open the 5 most ' +
    'important of them yourself and report what was missed; ' +
    '(b) whole categories of UI work not represented at all - e.g. onboarding and first-run, print/PDF and ' +
    'report layout, responsive breakpoints and tablet/desktop density, offline and slow-network ' +
    'presentation, toast/notification design, language switching, 404 and error pages, empty product ' +
    'state, keyboard-first power use, high-contrast theming, Android tablet and foldable, app icon and ' +
    'splash quality, store screenshots; ' +
    '(c) contradictions or double-counting between the findings. ' +
    'Return your own findings in the same schema, each with real citations from files you opened.\n\n' +
    'CONFIRMED FINDINGS:\n' +
    JSON.stringify(confirmed.map(function (f) {
      return { id: f.id, title: f.title, evidence: f.evidence }
    }), null, 1),
  { label: 'gaps:critic', phase: 'Gaps', schema: AUDIT_SCHEMA, effort: 'high' }
)

return {
  counts: {
    auditors: audits.length,
    raw: allFindings.length,
    confirmed: confirmed.length,
    refuted: refuted.length,
    unverified: unverified.length,
    gapFindings: critic && critic.findings ? critic.findings.length : 0,
  },
  summaries: audits.map(function (a, i) {
    return {
      dim: DIMENSIONS[i] ? DIMENSIONS[i].key : 'dim' + i,
      summary: a.summary,
      metrics: a.metrics || [],
      keep: a.keep || [],
    }
  }),
  confirmed: confirmed,
  refuted: refuted.map(function (f) { return { id: f.id, title: f.title, why: f.verifyNote } }),
  unverified: unverified.map(function (f) {
    return { id: f.id, title: f.title, evidence: f.evidence, severity: f.severity }
  }),
  gaps: critic,
}
