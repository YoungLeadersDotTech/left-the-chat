import { EMPTY_TELEMETRY, coerceTelemetry } from './schema.js'

function asArray(value) { return Array.isArray(value) ? value : [value] }
function number(value) { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0 }

function walk(value, visit, seen = new Set()) {
  if (!value || typeof value !== 'object' || seen.has(value)) return
  seen.add(value)
  visit(value)
  for (const child of Object.values(value)) {
    if (Array.isArray(child)) child.forEach((entry) => walk(entry, visit, seen))
    else walk(child, visit, seen)
  }
}

function parseRecords(raw) {
  const trimmed = (raw || '').trim()
  if (!trimmed) return []
  try { return asArray(JSON.parse(trimmed)) } catch {
    return trimmed.split(/\r?\n/).filter(Boolean).map((line, index) => {
      try { return JSON.parse(line) } catch { return { type: 'text', line: index + 1, content: line } }
    })
  }
}

function bump(counter, key) {
  if (!key) return
  counter[key] = (counter[key] || 0) + 1
}

/**
 * Normalise a raw session log into the frozen telemetry shape. Everything the declared-versus-
 * actual checks need is derived here, so a log that does not record something leaves the field
 * empty and the matching check simply does not fire.
 */
function normalize(records, source) {
  const toolCounts = {}
  const skillCounts = {}
  const agents = new Set()
  const errors = []
  const phaseSequence = []
  let tasksCreated = 0
  let inputTokens = 0
  let outputTokens = 0
  let durationMs = 0
  let environment = {}

  walk(records, (event) => {
    if (Array.isArray(event.tools)) event.tools.forEach((tool) => bump(toolCounts, String(tool)))
    if (Array.isArray(event.skillsFired)) event.skillsFired.forEach((skill) => bump(skillCounts, String(skill)))
    if (Array.isArray(event.agentsDispatched)) event.agentsDispatched.forEach((agent) => agents.add(String(agent)))
    if (Array.isArray(event.phaseSequence)) event.phaseSequence.forEach((phase) => phaseSequence.push(String(phase)))
    if (Array.isArray(event.errors)) event.errors.forEach((item) => errors.push(String(item?.message || item)))
    if (event.environment && typeof event.environment === 'object') environment = { ...environment, ...event.environment }

    const toolName = event.tool_name || event.toolName
      || ((event.name && /tool/i.test(String(event.type || ''))) ? event.name : null)
    if (toolName) {
      const name = String(toolName)
      bump(toolCounts, name)
      // A Skill call records which skill fired; a Task* call records task creation. Both are
      // tool invocations in the log, and both are what the runtime checks compare against.
      if (/^Skill$/i.test(name)) {
        const skill = event.input?.skill || event.parameters?.skill || event.arguments?.skill
        if (skill) bump(skillCounts, String(skill))
      }
      if (/^TaskCreate$/i.test(name)) tasksCreated += 1
      if (/^(Task|Agent)$/i.test(name)) {
        const agent = event.input?.subagent_type || event.parameters?.subagent_type || event.input?.agent
        if (agent) agents.add(String(agent))
      }
    }

    if (event.skill || event.skill_name) bump(skillCounts, String(event.skill || event.skill_name))
    if (event.subagent_type) agents.add(String(event.subagent_type))
    if (typeof event.tasksCreated === 'number') tasksCreated += event.tasksCreated
    if (event.phase !== undefined && event.phase !== null && !Array.isArray(event.phase)) {
      phaseSequence.push(String(event.phase))
    }

    const isError = event.error || event.is_error || event.status === 'error' || event.type === 'error'
    if (isError) errors.push(String(event.error?.message || event.error || event.message || 'Unhandled runtime error'))

    const usage = event.usage || event.token_usage || {}
    inputTokens += number(usage.input_tokens ?? usage.prompt_tokens ?? event.inputTokens)
    outputTokens += number(usage.output_tokens ?? usage.completion_tokens ?? event.outputTokens)
    durationMs += number(event.duration_ms ?? event.durationMs ?? event.latency_ms)
  })

  return coerceTelemetry({
    source,
    tools: Object.keys(toolCounts),
    toolCounts,
    skillsFired: Object.keys(skillCounts),
    skillCounts,
    agentsDispatched: [...agents],
    tasksCreated,
    phaseSequence,
    errors,
    environment,
    metrics: { durationMs, inputTokens, outputTokens }
  })
}

export function parseClaudeCodeLog(raw) { return normalize(parseRecords(raw), 'claude-code') }

// T-12e: this was called parseOpenCodeLog and the strategy was 'opencode', on an assumption
// nobody had checked against a real install. Checked one: OpenCode keeps session data in a
// SQLite database (~/.local/share/opencode/opencode.db), not a JSON or JSONL log file, and its
// tool-call rows carry a bare `tool` field rather than `tool_name`/`toolName`, so this walker
// would produce near-zero counts against real OpenCode data with no error shown. The walker
// itself is a reasonable generic JSON/JSONL normalizer - it just is not an OpenCode parser, so
// it is renamed to say what it actually does.
export function parseGenericLog(raw) { return normalize(parseRecords(raw), 'generic') }

// T-47: people paste the agent's whole reply, not a bare object. Claude answers with a sentence,
// a fenced block, and often a summary underneath. The old code called JSON.parse on the entire
// paste, failed, and fell through to the log walker, which found almost nothing and said so
// quietly - the worst possible failure for a step whose whole job is "paste what came back".
// Reported by John at 15:16 doing exactly that.
//
// Scan for the first balanced JSON object that carries a schemaVersion, in document order, and
// use it. Document order keeps this deterministic: the same paste always yields the same object.
export function extractProbeObject(text) {
  const source = text || ''
  for (let i = 0; i < source.length; i += 1) {
    if (source[i] !== '{') continue
    let depth = 0
    let inString = false
    let escaped = false
    for (let j = i; j < source.length; j += 1) {
      const ch = source[j]
      if (escaped) { escaped = false; continue }
      if (ch === '\\' && inString) { escaped = true; continue }
      if (ch === '"') { inString = !inString; continue }
      if (inString) continue
      if (ch === '{') depth += 1
      else if (ch === '}') {
        depth -= 1
        if (depth === 0) {
          const candidate = source.slice(i, j + 1)
          try {
            const parsed = JSON.parse(candidate)
            if (parsed && !Array.isArray(parsed) && parsed.schemaVersion !== undefined) return parsed
          } catch { /* not valid JSON, keep scanning from the next brace */ }
          break
        }
      }
    }
  }
  return null
}

export function parseTelemetry(raw, strategy = 'auto') {
  const trimmed = (raw || '').trim()
  if (!trimmed) return { ...EMPTY_TELEMETRY }

  // The probe's own answer already is the frozen shape. Take it as given rather than re-deriving
  // it from a walk, which would double-count anything the agent reported both ways.
  try {
    const direct = JSON.parse(trimmed)
    if (direct && !Array.isArray(direct) && direct.schemaVersion !== undefined) return coerceTelemetry(direct)
  } catch { /* not a single probe object, try to find one inside the paste */ }

  const embedded = extractProbeObject(trimmed)
  if (embedded) return coerceTelemetry(embedded)

  if (strategy === 'claude-code') return parseClaudeCodeLog(trimmed)
  if (strategy === 'generic') return parseGenericLog(trimmed)
  const lower = trimmed.toLowerCase()
  return lower.includes('sessionid') || lower.includes('tool_use')
    ? parseClaudeCodeLog(trimmed)
    : parseGenericLog(trimmed)
}
