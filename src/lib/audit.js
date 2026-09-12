import { stableStringify } from './deterministic.js'
import { compareDeclaredWithActual, inspectSetup, severityRank } from './checks.js'
import { PROBE_SCHEMA, TELEMETRY_SCHEMA_VERSION, coerceTelemetry } from './schema.js'

export { inspectSetup }

// Reference rates, carried with a version and a date so the estimate can never be mistaken for a
// live price (plan decision D-13). Tokens are reported as fact; this is the only estimate here.
const PRICING_TABLE = {
  version: '2026-09-v1',
  captured: '2026-09-12',
  inputUsdPerMillion: 3,
  outputUsdPerMillion: 15
}

export function enrichAudit(staticAudit, rawTelemetry) {
  const telemetry = coerceTelemetry(rawTelemetry)
  const findings = [
    ...staticAudit.findings,
    ...compareDeclaredWithActual(staticAudit.declared, telemetry)
  ]
  findings.sort((a, b) => severityRank(a.severity) - severityRank(b.severity) || a.id.localeCompare(b.id))

  const estimatedCostUsd = Number((
    (telemetry.metrics.inputTokens / 1000000) * PRICING_TABLE.inputUsdPerMillion
    + (telemetry.metrics.outputTokens / 1000000) * PRICING_TABLE.outputUsdPerMillion
  ).toFixed(6))

  return {
    reportVersion: 2,
    schemaVersion: TELEMETRY_SCHEMA_VERSION,
    schemaMismatch: telemetry.schemaVersion !== TELEMETRY_SCHEMA_VERSION
      ? `Telemetry declares schema v${telemetry.schemaVersion}, this page reads v${TELEMETRY_SCHEMA_VERSION}. Runtime findings may be incomplete.`
      : null,
    pricingTable: PRICING_TABLE,
    declared: staticAudit.declared,
    actual: telemetry,
    metrics: {
      ...telemetry.metrics,
      estimatedCostUsd,
      errorCount: telemetry.errors.length,
      findingCount: findings.length,
      criticalCount: findings.filter((item) => item.severity === 'critical').length,
      majorCount: findings.filter((item) => item.severity === 'major').length
    },
    findings
  }
}

/**
 * Prompt A: the probe. Read-only by construction, and it carries an environment probe because a
 * web page cannot see what is installed on the machine, and Prompt B has to know before it is
 * written (plan task T-12a).
 */
// Cap on how much source text rides along in the prompt. Big enough for any realistic prompt,
// skill or AGENTS.md; small enough that dropping a whole plugin folder does not produce something
// nobody can paste.
const EMBED_BUDGET = 24000

function embedSources(files) {
  if (!files || !files.length) return ''
  const blocks = []
  let spent = 0
  for (const file of files) {
    const body = file.content || ''
    const remaining = EMBED_BUDGET - spent
    if (remaining <= 0) {
      blocks.push(`### ${file.name}\n(omitted, prompt size budget reached)`)
      continue
    }
    const clipped = body.length > remaining
    const shown = clipped ? `${body.slice(0, remaining)}\n...(truncated at ${remaining.toLocaleString()} characters)` : body
    spent += shown.length
    blocks.push(`### ${file.name}\n\n\`\`\`\n${shown}\n\`\`\``)
  }
  return blocks.join('\n\n')
}

export function buildPromptA(staticAudit, files) {
  const declared = stableStringify(staticAudit.declared)
  const sources = embedSources(files || staticAudit.sources)
  // The prompt has to visibly change with the input, or the user cannot tell the page did
  // anything before they copy it. The declared surface alone is empty for any file without
  // frontmatter, which is most low-trust pastes, so the static findings carry that signal.
  // This block is FIRST in the prompt, deliberately. It was appended at the bottom until
  // 2026-09-12, where it sat at line 80 of 88 inside a 150px scroll box, so every prompt looked
  // like identical boilerplate and users correctly concluded the page had done nothing. The
  // content was always there; being unreadable made it worthless.
  const summary = staticAudit.files.length
    ? [
        `# Audit of ${staticAudit.files.length} file${staticAudit.files.length === 1 ? '' : 's'}: ${staticAudit.files.join(', ')}`,
        '',
        staticAudit.findings.length
          ? `${staticAudit.findings.length} finding${staticAudit.findings.length === 1 ? '' : 's'} from the files alone, before any run was measured:`
          : 'No static findings. The files are clean on everything checkable without a run.',
        ...staticAudit.findings.map((item) => `- [${item.severity}] ${item.id}: ${item.title}`),
        '',
        'Confirm or contradict these where the run gives you evidence. Do not re-derive them.'
      ].join('\n')
    : '# Nothing loaded\n\nNo files were given to the page, so there are no static findings. Report on the session anyway.'
  return `${summary}
${sources ? `
## The prompt being audited

This is the exact text the findings above refer to. Judge it as written, and if you disagree with
a finding say so and say why.

${sources}
` : ''}
Now run a read-only probe of your own session and return the result.

You are being asked to report on yourself. This is a read-only probe: do not edit, create,
move, or delete any file, and do not run anything that changes state.

Gather the following about the session or sessions that ran this prompt, then return JSON and
nothing else.

1. Every tool actually invoked, with a call count for each.
2. Every skill that actually fired, with a fire count for each.
3. Every subagent actually dispatched, by name.
4. How many tasks were created via the task tools. Zero is a real answer, report it.
5. The phases or numbered steps in the order they actually ran.
6. Every error surfaced to the user.
7. Token usage and wall-clock duration.
8. An environment probe: operating system, \`python3 --version\` (null if not installed), this
   agent's own name and version, the current git branch (null if not a git repo), and whether the
   working tree is dirty.

Where to look: Claude Code writes session logs under \`~/.claude/projects/<slugified-path>/\`,
where the slug is the launch directory with \`/\` and \`.\` replaced by \`-\`. Most other agents,
OpenCode included, do not expose a text session log to read - if that is you, skip straight to the
fallback below.

**If you cannot find a session log, do not give up and do not guess.** Answer from what you can
observe in this session, set anything you genuinely cannot determine to null, and then do one more
thing: start recording from here. Append one JSON line per tool call to \`./.left-the-chat/session.jsonl\`
for the rest of this session, each line \`{"tool_name":"...","skill":"...","usage":{...},"phase":"..."}\`.
Tell the user that path. The second measurement will then have a log to read even though the first
did not, which is the whole point of a before-and-after.

This is why this loop does not need to know where your agent keeps its logs. If it has them, it
reads them. If it does not, it asks you to make them. Any agent that can append to a file can
complete this loop.

Return exactly this shape, schema version ${TELEMETRY_SCHEMA_VERSION}:

${JSON.stringify(PROBE_SCHEMA, null, 2)}

One thing to establish before you answer, because it changes what the numbers mean. Search your
own session logs for the prompt above. If you cannot find a session that actually ran it, say so
plainly after the object: the telemetry you are about to report describes the session you are in
now, which is the session doing the auditing, and its tokens and duration are the cost of this
audit rather than the cost of that prompt. Saying nothing lets the page present one as the other.

Answer with that object and nothing else. No preamble, no summary underneath. If you have
something to say about the findings, or about whether the prompt was ever run, say it after the
object.

Then put the object on the clipboard so it survives the trip back to the page intact. On macOS,
pipe it through \`pbcopy\`. On Windows, pipe it through \`clip\`. On Linux, \`xclip
-selection clipboard\`. Copying the object alone rather than your whole reply is the difference
between a report and a shrug.

Declared surface read from those files. Do not copy it into your answer, report what actually
happened:

${declared}`
}

// Carried as text so that a machine with Python gets the full-depth checks without installing
// anything from this page (plan decision D-09).
const PYTHON_DEPTH_CHECKS = `# Optional, only if the probe reported python3 available.
# Full-depth static pass over the same files, for the checks the browser build does not carry.
python3 - <<'PY'
import pathlib, re, sys
CAP = 250
bad = 0
for path in sorted(pathlib.Path('.').rglob('*.md')):
    text = path.read_text(errors='replace')
    front = re.match(r'^---\\n(.*?)\\n---', text, re.S)
    if not front:
        continue
    desc = re.search(r'^description:\\s*(.+)$', front.group(1), re.M)
    if not desc:
        print(f'{path}: no description'); bad += 1
    elif len(desc.group(1)) > CAP:
        print(f'{path}: description {len(desc.group(1))} chars, cap {CAP}'); bad += 1
print(f'{bad} finding(s)')
sys.exit(0)
PY`

/**
 * Prompt B: the fix plan. Deliberately an exemplar of the patterns this auditor grades, because a
 * tool that tells you to gate destructive work and then rewrites your files unasked has argued
 * against itself (plan decision D-11).
 */
export function buildPromptB(report) {
  const blocking = report.findings
    .filter((item) => item.severity === 'critical' || item.severity === 'major')
    .map(({ id, severity, title, detail, source }) => ({ id, severity, source, title, detail }))
  const hasPython = Boolean(report.actual?.environment?.python3)
  const dirty = report.actual?.environment?.gitDirty === true
  const branch = report.actual?.environment?.gitWorktree

  return `Fix the prompt findings below. Before you change anything, follow this gate.

## Step 1. Ask, do not assume

Use your structured-question tool (\`AskUserQuestion\` in Claude Code, the equivalent elsewhere) to
ask exactly this, and wait for an answer:

  "How should I apply ${blocking.length} finding${blocking.length === 1 ? '' : 's'}?"
  A) Dry run. Show me every edit as a diff and write nothing. (Recommended)
  B) Write the files, but commit everything first so rollback is one command.
  C) Just do it.

${dirty
  ? `The probe reported the working tree is dirty${branch ? ` on \`${branch}\`` : ''}. Say so when you
ask, and make option B commit the existing work on its own before touching anything here, so the
rollback boundary is clean.`
  : `The probe reported a clean working tree${branch ? ` on \`${branch}\`` : ''}.`}

If the answer is A, produce the diffs and then ask a second question: "Apply these now?" Do not
apply on the strength of the first answer.

Then ask which findings, because the cheapest useful loop is rarely the complete one:

  "Which findings should I close?"
  A) The ${report.metrics.criticalCount} critical only, then re-measure. (Recommended first pass)
  B) Critical and major, ${blocking.length} in total.
  C) Everything, including style and prose.

Recommend A on the first pass and say why: the first run is where most of the token cost sits, so
closing the expensive findings and re-measuring shows the largest delta for the least work, and
the next pass starts from a smaller list.

## Step 2. Rules for the edits

- Never widen a permission to resolve a finding. If a tool is used but not granted, the answer is
  either to declare it deliberately or to stop using it, and that is a decision for the human.
- Smallest change that closes the finding. Do not reformat, reorder, or improve anything adjacent.
- Do not delete a skill or agent to resolve a never-fired finding. Fix the description first.
- Preserve behaviour that currently works.

## Step 3. Re-probe

When the edits are applied, run the original probe again unchanged and return the telemetry JSON.
The comparison is only meaningful if the second measurement uses the same probe as the first.

${hasPython ? `## Step 4. Full-depth pass\n\nThe probe reported python3 available, so also run this:\n\n\`\`\`bash\n${PYTHON_DEPTH_CHECKS}\n\`\`\`\n` : `## Step 4. Skipped\n\nThe probe reported no python3, so the browser-side findings above are the full set. That is a\nreal limit of this run, not a clean bill of health.\n`}
## Findings

${stableStringify(blocking)}`
}
