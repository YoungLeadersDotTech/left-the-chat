function asArray(value) { return Array.isArray(value) ? value : [value] }
function number(value) { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0 }

function walk(value, visit) {
  if (!value || typeof value !== 'object') return
  visit(value)
  for (const child of Object.values(value)) {
    if (Array.isArray(child)) child.forEach((entry) => walk(entry, visit))
    else walk(child, visit)
  }
}

function parseRecords(raw) {
  const trimmed = raw.trim()
  if (!trimmed) return []
  try { return asArray(JSON.parse(trimmed)) } catch {
    return trimmed.split(/\r?\n/).filter(Boolean).map((line, index) => {
      try { return JSON.parse(line) } catch { return { type: 'text', line: index + 1, content: line } }
    })
  }
}

function normalize(records, source) {
  const tools = []
  const errors = []
  let inputTokens = 0
  let outputTokens = 0
  let durationMs = 0

  walk(records, (event) => {
    if (Array.isArray(event.tools)) tools.push(...event.tools.map(String))
    if (Array.isArray(event.errors)) errors.push(...event.errors.map((item) => String(item?.message || item)))
    const candidate = event.tool_name || event.toolName || ((event.name && /tool/i.test(event.type || '')) ? event.name : null)
    if (candidate) tools.push(String(candidate))
    const isError = event.error || event.is_error || event.status === 'error' || event.type === 'error'
    if (isError) errors.push(String(event.error?.message || event.error || event.message || 'Unhandled runtime error'))
    const usage = event.usage || event.token_usage || {}
    inputTokens += number(usage.input_tokens ?? usage.prompt_tokens ?? event.inputTokens)
    outputTokens += number(usage.output_tokens ?? usage.completion_tokens ?? event.outputTokens)
    durationMs += number(event.duration_ms ?? event.durationMs ?? event.latency_ms)
  })

  return {
    schemaVersion: 1,
    source,
    tools: [...new Set(tools)].sort(),
    errors: [...new Set(errors)].sort(),
    metrics: { durationMs, inputTokens, outputTokens, totalTokens: inputTokens + outputTokens }
  }
}

export function parseClaudeCodeLog(raw) { return normalize(parseRecords(raw), 'claude-code') }
export function parseOpenCodeLog(raw) { return normalize(parseRecords(raw), 'opencode') }

export function parseTelemetry(raw, strategy = 'auto') {
  if (strategy === 'claude-code') return parseClaudeCodeLog(raw)
  if (strategy === 'opencode') return parseOpenCodeLog(raw)
  const lower = raw.toLowerCase()
  return lower.includes('sessionid') || lower.includes('tool_use')
    ? parseClaudeCodeLog(raw)
    : parseOpenCodeLog(raw)
}
