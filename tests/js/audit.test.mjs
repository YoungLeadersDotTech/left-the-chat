// Proves the central product claim: same input, byte-identical output, every time.
// Run with `npm test`. No framework, so it costs nothing to keep in the loop on build day.

import assert from 'node:assert/strict'
import { inspectSetup } from '../../src/lib/audit.js'
import { enrichAudit, buildPromptA, buildPromptB } from '../../src/lib/audit.js'
import { parseTelemetry } from '../../src/lib/parsers.js'
import { sha256 } from '../../src/lib/deterministic.js'

const FIXTURE_FILES = [
  {
    name: 'skills/tidy-up/SKILL.md',
    content: `---
name: tidy-up
description: ${'Tidies things up in the repository and generally makes everything nicer for everyone involved in the project at any time. '.repeat(3)}
allowed-tools: Read, Write, Bash, TaskCreate
---

## Phase 1: Discover
Look at the files.

## Phase 2: Apply
Change the files. See [the reference](references/missing-reference.md) for detail.
Always do this. Never skip it.
`
  },
  {
    name: 'agents/reviewer.md',
    content: `---
name: reviewer
description: Reviews things.
tools: Read, Grep
---
Review the diff.
`
  }
]

const FIXTURE_TELEMETRY = JSON.stringify({
  schemaVersion: 2,
  source: 'claude-code',
  tools: ['Read', 'Bash', 'WebFetch'],
  toolCounts: { Read: 12, Bash: 4, WebFetch: 1 },
  skillsFired: ['tidy-up'],
  skillCounts: { 'tidy-up': 9, 'other-skill': 1 },
  agentsDispatched: [],
  tasksCreated: 0,
  phaseSequence: ['2 Apply', '1 Discover'],
  errors: ['Bash: command not found: rg'],
  environment: { os: 'darwin', python3: '3.12.4', agent: 'claude-code 2.x', gitWorktree: 'main', gitDirty: true },
  metrics: { durationMs: 41230, inputTokens: 184000, outputTokens: 9100 }
})

function run() {
  return enrichAudit(inspectSetup(FIXTURE_FILES), parseTelemetry(FIXTURE_TELEMETRY, 'auto'))
}

const first = run()
const second = run()

// 1. Determinism. This is the claim the whole product rests on.
assert.equal(await sha256(first), await sha256(second), 'two runs of the same input must hash identically')
assert.notEqual(await sha256(first), '', 'hash must be non-empty')

// 2. Reordering the input files must not change the result. Sorting is what makes that true, and
//    it is the easiest thing to break later.
const reversed = enrichAudit(inspectSetup([...FIXTURE_FILES].reverse()), parseTelemetry(FIXTURE_TELEMETRY, 'auto'))
assert.equal(await sha256(first), await sha256(reversed), 'file order must not affect the report')

const ids = first.findings.map((item) => item.id)
const has = (prefix) => ids.some((id) => id.startsWith(prefix))

// 3. Static checks (T-11a).
assert.ok(has('CFG-014:'), 'over-cap description must be flagged')
assert.ok(has('REF-001:'), 'dead file reference must be flagged')
assert.ok(has('CFG-017') || has('STYLE-001'), 'absolute language with no exception must be flagged')

// 4. Declared versus actual (T-11b). These are the findings no static linter can produce.
assert.ok(has('RUN-TOOL-UNUSED:Write'), 'granted-but-unused tool must be flagged')
assert.ok(has('RUN-TOOL-UNDECLARED:WebFetch'), 'used-but-ungranted tool must be flagged')
assert.ok(has('RUN-SKILL-NEVER-FIRED:reviewer') || has('RUN-AGENT-NEVER-DISPATCHED:reviewer'), 'never-used declaration must be flagged')
assert.ok(has('RUN-TASK-NONE'), 'Task tools granted with zero tasks created must be flagged')
assert.ok(has('RUN-SKILL-GREEDY:tidy-up'), 'a skill taking most of the routing must be flagged')
assert.ok(has('RUN-PHASE-ORDER'), 'phases running out of declared order must be flagged')
assert.ok(has('RUN-ERROR-000'), 'runtime errors must surface as findings')

// 5. Severity ordering is by rank, not alphabetical accident.
const ranks = first.findings.map((item) => ({ critical: 0, major: 1, minor: 2 }[item.severity]))
assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b), 'findings must be ordered critical, major, minor')

// 6. Prompt B has to be the exemplar it grades (decision D-11).
const promptB = buildPromptB(first)
assert.match(promptB, /AskUserQuestion/, 'Prompt B must gate with a structured question')
assert.match(promptB, /Dry run/, 'Prompt B must offer a dry run')
assert.match(promptB, /Never widen a permission/, 'Prompt B must refuse to fix findings by widening access')
assert.match(promptB, /python3 -/, 'Prompt B must carry the Python depth checks when python3 is available')

// 7. Prompt A must ask for everything the runtime checks need, or those checks can never fire.
const promptA = buildPromptA(inspectSetup(FIXTURE_FILES))
for (const field of ['skillsFired', 'agentsDispatched', 'tasksCreated', 'phaseSequence', 'python3']) {
  assert.match(promptA, new RegExp(field), `Prompt A must probe for ${field}`)
}

// 8. Prompt A must carry the write-your-own-log fallback. This is what makes the loop work on an
//    agent whose log location nobody knows, Codex included, without writing a parser for it.
assert.match(promptA, /session\.jsonl/, 'Prompt A must name a path to record to when no log is found')
assert.match(promptA, /do not guess/i, 'Prompt A must forbid guessing when the log is absent')

// 9. Prompt B must let the user pick how much to close, and recommend the cheap first pass.
assert.match(promptB, /Which findings should I close/, 'Prompt B must offer a findings scope choice')
assert.match(promptB, /Recommended first pass/, 'Prompt B must recommend critical-only first')

// 10. No python3 in the environment means Prompt B says so rather than pretending.
const noPython = enrichAudit(inspectSetup(FIXTURE_FILES), parseTelemetry(
  JSON.stringify({ schemaVersion: 2, environment: { python3: null }, tools: [], metrics: {} }), 'auto'))
assert.match(buildPromptB(noPython), /not a clean bill of health/, 'a missing depth pass must be stated, not hidden')

// 11. The pre-commit auditor's block condition (T-12d). The hook exits non-zero on any critical
//     finding, so a skill with no description must produce one. Verified live: exit 1 on this
//     input, exit 0 once a description is added.
const hookInput = [{ name: 'skills/x/SKILL.md', content: '---\nname: x\nallowed-tools: Read\n---\nDo it.\n' }]
assert.ok(
  inspectSetup(hookInput).findings.some((item) => item.severity === 'critical' && item.id.startsWith('CFG-013')),
  'a skill with no description must be a critical finding, which is what the commit hook blocks on'
)

console.log(`PASS  ${first.findings.length} findings, ${first.metrics.criticalCount} critical, ${first.metrics.majorCount} major`)
console.log(`      hash ${(await sha256(first)).slice(0, 16)} stable across 3 runs`)
