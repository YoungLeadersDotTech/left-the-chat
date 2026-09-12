// Static checks (plan task T-11a) and the declared-versus-actual family (T-11b).
//
// Everything here is a pure function of its inputs. No clock, no randomness, no network, no
// iteration order that depends on anything but a sort. That is what lets the page hash a report
// and claim the same input produces the same output, which is the whole product claim.

const SEVERITY_ORDER = { critical: 0, major: 1, minor: 2 }

export function severityRank(severity) {
  return severity in SEVERITY_ORDER ? SEVERITY_ORDER[severity] : 99
}

export function finding(id, severity, title, detail, source = 'configuration') {
  return { id, severity, title, detail, source }
}

// Anthropic's published cap on a skill or agent description.
const DESCRIPTION_CAP = 250

const CREDENTIAL_PATTERNS = [
  [/\bsk-[A-Za-z0-9]{16,}\b/, 'an OpenAI-style secret key'],
  [/\bghp_[A-Za-z0-9]{20,}\b/, 'a GitHub personal access token'],
  [/\bxox[baprs]-[A-Za-z0-9-]{10,}\b/, 'a Slack token'],
  // split so this detector's own source doesn't contain a key-shaped string
  [new RegExp('\\bAKIA' + '[0-9A-Z]{16}\\b'), 'an AWS access key id'],
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----/, 'a private key block']
]

const CONTACT_PATTERNS = [
  [/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/, 'an email address'],
  [/\b\+?\d[\d\s().-]{8,}\d\b/, 'something shaped like a phone number']
]

function parseFrontmatter(content) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---/.exec(content)
  if (!match) return null
  const fields = {}
  let key = null
  for (const line of match[1].split(/\r?\n/)) {
    const pair = /^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$/.exec(line)
    if (pair) {
      key = pair[1]
      fields[key] = pair[2].trim()
    } else if (key && /^\s+\S/.test(line)) {
      fields[key] = `${fields[key]} ${line.trim()}`.trim()
    }
  }
  return fields
}

function splitList(value) {
  if (!value) return []
  return [...new Set(
    value.replace(/^\[|\]$/g, '').split(',').map((item) => item.replace(/["'`]/g, '').trim()).filter(Boolean)
  )].sort()
}

function isAgentFile(name) {
  return /(^|\/)agents\//.test(name) || /\.agent\.md$/.test(name)
}

function isSkillFile(name) {
  return /(^|\/)SKILL\.md$/i.test(name) || /(^|\/)skills\//.test(name)
}

/**
 * Read the declared surface out of the dropped files, and run every check that needs only the
 * files themselves. Runs on drop, before any round trip, which is what earns the first copy-paste.
 */
export function inspectSetup(files) {
  const ordered = [...(files || [])].sort((a, b) => a.name.localeCompare(b.name))
  const findings = []
  const tools = new Set()
  const skills = new Set()
  const agents = new Set()
  const declaredPhases = []
  let declaresTaskTools = false
  let combinedLength = 0

  const names = new Set(ordered.map((file) => file.name))
  const basenames = new Set(ordered.map((file) => file.name.split('/').pop()))

  if (!ordered.length) {
    findings.push(finding('CFG-001', 'critical', 'No setup files loaded',
      'Add a skill, agent, prompt, or pasted instructions before running the audit.'))
    return { files: [], declared: { tools: [], skills: [], agents: [], phases: [], declaresTaskTools: false }, findings }
  }

  for (const file of ordered) {
    const content = file.content || ''
    combinedLength += content.length
    const front = parseFrontmatter(content)
    const body = front ? content.slice(content.indexOf('---', 3) + 3) : content
    const label = file.name
    const structured = isSkillFile(label) || isAgentFile(label)

    if (structured && !front) {
      findings.push(finding(`CFG-010:${label}`, 'critical', 'No frontmatter block',
        `${label} looks like a skill or agent definition but has no \`---\` frontmatter, so the runner cannot read its name, description, or tool grant.`))
    }

    if (front) {
      const name = front.name || ''
      const description = front.description || ''
      const granted = splitList(front['allowed-tools'] || front.tools || '')
      granted.forEach((tool) => tools.add(tool))
      if (granted.some((tool) => /^Task/.test(tool))) declaresTaskTools = true

      if (isAgentFile(label) && name) agents.add(name)
      else if (name) skills.add(name)

      if (!name) {
        findings.push(finding(`CFG-011:${label}`, 'major', 'No name in frontmatter',
          `${label} declares no \`name:\`, so nothing can reference or dispatch it by name.`))
      } else if (!/^[a-z0-9]+(-[a-z0-9]+)*(:[a-z0-9]+(-[a-z0-9]+)*)?$/.test(name)) {
        findings.push(finding(`CFG-012:${label}`, 'minor', 'Name is not kebab-case',
          `\`${name}\` is not lower-case kebab. Invocation is name-sensitive, so mixed case is a silent miss.`))
      }

      if (!description) {
        findings.push(finding(`CFG-013:${label}`, 'critical', 'No description in frontmatter',
          `${label} has no \`description:\`. The runner must read the whole file to guess when to use it, which is the single most expensive avoidable cost in a prompt.`))
      } else {
        if (description.length > DESCRIPTION_CAP) {
          findings.push(finding(`CFG-014:${label}`, 'major', `Description is ${description.length} characters, cap is ${DESCRIPTION_CAP}`,
            `${label} exceeds the published ${DESCRIPTION_CAP}-character description cap by ${description.length - DESCRIPTION_CAP}. Over the cap the description may be truncated, and a truncated trigger phrase fires unpredictably.`))
        }
        if (!/\b(not|skip|never|instead|rather than|do not)\b/i.test(description)) {
          findings.push(finding(`CFG-015:${label}`, 'minor', 'Description says when to use, never when not to',
            `${label} gives no negative trigger. Without one the runner has nothing to rule the skill out with, so it fires on adjacent work.`))
        }
        if (description.length < 40) {
          findings.push(finding(`CFG-016:${label}`, 'minor', 'Description is very short',
            `${label} has a ${description.length}-character description. Too little to route on, so the runner falls back to reading the body.`))
        }
      }
    }

    // Dead references: a link or path pointing at a file that is not in what was dropped.
    const referenced = new Set()
    for (const match of body.matchAll(/\]\(([^)\s#]+\.(?:md|py|js|json|sh|ya?ml))[^)]*\)/g)) referenced.add(match[1])
    for (const match of body.matchAll(/`([\w./-]+\.(?:md|py|js|json|sh|ya?ml))`/g)) referenced.add(match[1])
    for (const ref of [...referenced].sort()) {
      if (/^(https?:|~|\$)/.test(ref)) continue
      const base = ref.split('/').pop()
      if (names.has(ref) || basenames.has(base)) continue
      // At low trust there is exactly one pasted file, so an outgoing reference is unresolvable
      // by construction rather than by fault. That is an honest, self-evident limit, so the
      // finding carries its own remedy instead of the page asking for more access.
      const singleFile = ordered.length === 1
      findings.push(finding(`REF-001:${label}:${ref}`, singleFile ? 'minor' : 'major',
        'Reference points at a file that is not here',
        singleFile
          ? `${label} references \`${ref}\`, and only one file was loaded, so this cannot be checked from here. Switch to Medium trust and drop the whole folder in, and every reference gets verified instead of assumed.`
          : `${label} references \`${ref}\`, which is not among the files loaded. Either it was not included in the drop, or the reference is dead and the runner will burn a tool call discovering that.`))
    }

    for (const [pattern, what] of CREDENTIAL_PATTERNS) {
      if (pattern.test(content)) {
        findings.push(finding(`SEC-001:${label}`, 'critical', 'Something shaped like a credential is in the file',
          `${label} contains ${what}. Rotate it. Agent instruction files get committed, shared, and pasted into chats far more casually than code does.`))
        break
      }
    }
    for (const [pattern, what] of CONTACT_PATTERNS) {
      if (pattern.test(content)) {
        findings.push(finding(`PII-001:${label}`, 'major', 'Personal contact detail in the file',
          `${label} contains ${what}. Instruction files travel further than the people in them expect.`, 'privacy'))
        break
      }
    }

    if (/(^|[^~\w])\/(Users|home)\/[A-Za-z0-9._-]+\//.test(content)) {
      findings.push(finding(`CFG-017:${label}`, 'major', 'Hard-coded home directory',
        `${label} contains an absolute path under a named home directory. It will not resolve on anyone else's machine. Use \`~/\`.`))
    }

    for (const match of body.matchAll(/^#{2,3}\s*(?:Phase|Step)\s+([0-9]+[a-z]?)\b[:.\s-]*(.*)$/gim)) {
      declaredPhases.push(`${match[1]}${match[2] ? ` ${match[2].trim()}` : ''}`)
    }
  }

  const combined = ordered.map((file) => `--- ${file.name}\n${file.content}`).join('\n')

  if (!tools.size) {
    findings.push(finding('CFG-002', 'critical', 'Tool permissions are implicit',
      'Nothing declares an explicit tool allowlist, so there is no declared surface to compare runtime access against. This is the check that makes every runtime finding below possible, which is why it is critical rather than advisory.'))
  }

  if (declaresTaskTools && !/\bTaskCreate\b/.test(combined)) {
    findings.push(finding('CFG-018', 'major', 'Task tools granted but never used in the instructions',
      'A `Task*` tool is in the allowlist but no instruction tells the runner to call `TaskCreate`. A granted-but-unmentioned tool is a permission with no purpose, and the runner will not infer the workflow from the grant alone.'))
  }

  if (declaredPhases.length >= 2 && !/\bTaskCreate\b/.test(combined)) {
    findings.push(finding('CFG-019', 'minor', `${declaredPhases.length} phases declared with no task tracking`,
      'Multi-phase instructions with no task chain lose their place when the session compacts. There is nothing outside the context window recording which phase finished.'))
  }

  if (/\b(always|never)\b/i.test(combined) && !/\b(except|unless|exception)\b/i.test(combined)) {
    findings.push(finding('STYLE-001', 'minor', 'Absolute instruction language with no stated exception',
      'Rules phrased as always or never, with no exception anywhere, tend to be either unenforceable or wrong at the edges. Say what the exception is.', 'prose'))
  }

  if (combinedLength > 12000) {
    findings.push(finding('STYLE-002', 'minor', `Instruction surface is ${combinedLength.toLocaleString()} characters`,
      'Above roughly 12,000 characters the runner is paying to read reference material on every invocation. Split the core rules from the reference.', 'prose'))
  }

  if (!/```/.test(combined) && combinedLength > 2000) {
    findings.push(finding('STYLE-003', 'minor', 'No worked example anywhere',
      'A long instruction file with no code block or literal example leaves every concrete decision to inference.', 'prose'))
  }

  findings.sort((a, b) => severityRank(a.severity) - severityRank(b.severity) || a.id.localeCompare(b.id))

  return {
    files: ordered.map((file) => file.name),
    declared: {
      tools: [...tools].sort(),
      skills: [...skills].sort(),
      agents: [...agents].sort(),
      phases: declaredPhases,
      declaresTaskTools
    },
    findings
  }
}

/**
 * The declared-versus-actual family (T-11b). This is the part a static linter structurally cannot
 * do, because every check here needs both halves: what the setup claims, and what the run did.
 */
export function compareDeclaredWithActual(declared, telemetry) {
  const findings = []
  const fired = new Set(telemetry.skillsFired)
  const dispatched = new Set(telemetry.agentsDispatched)
  const used = new Set(telemetry.tools)

  for (const tool of declared.tools) {
    if (!used.has(tool)) {
      findings.push(finding(`RUN-TOOL-UNUSED:${tool}`, 'major', `Tool granted but never used: ${tool}`,
        `${tool} is in the allowlist and the run never invoked it. Either the instructions never reach for it, or the grant is left over. An unused grant is pure attack surface.`, 'runtime'))
    }
  }

  if (declared.tools.length) {
    for (const tool of telemetry.tools) {
      if (!used.size || declared.tools.includes(tool)) continue
      findings.push(finding(`RUN-TOOL-UNDECLARED:${tool}`, 'critical', `Tool used but never granted: ${tool}`,
        `The run invoked ${tool}, which appears in no allowlist in the files loaded. Either a declaration is missing here, or something is reaching outside the surface you think you configured.`, 'runtime'))
    }
  }

  for (const skill of declared.skills) {
    if (!fired.has(skill)) {
      findings.push(finding(`RUN-SKILL-NEVER-FIRED:${skill}`, 'major', `Skill declared but never fired: ${skill}`,
        `${skill} carries trigger phrases and the run never invoked it. Either its description does not match how the work is actually described, or it is dead weight being read on every routing decision.`, 'runtime'))
    }
  }

  const firedTotal = Object.values(telemetry.skillCounts).reduce((sum, count) => sum + (Number(count) || 0), 0)
  for (const [skill, rawCount] of Object.entries(telemetry.skillCounts).sort(([a], [b]) => a.localeCompare(b))) {
    const count = Number(rawCount) || 0
    if (count >= 5 && firedTotal && count / firedTotal > 0.5) {
      findings.push(finding(`RUN-SKILL-GREEDY:${skill}`, 'major', `Skill fired ${count} times, ${Math.round((count / firedTotal) * 100)}% of all firings: ${skill}`,
        `A single skill taking most of the routing usually means its description is too greedy rather than that the work was uniform. It is being selected for adjacent tasks other skills should own.`, 'runtime'))
    }
  }

  for (const agent of declared.agents) {
    if (!dispatched.has(agent)) {
      findings.push(finding(`RUN-AGENT-NEVER-DISPATCHED:${agent}`, 'major', `Agent declared but never dispatched: ${agent}`,
        `${agent} is defined and the run never delegated to it. Agent definitions are read during routing whether or not they are used.`, 'runtime'))
    }
  }

  if (declared.declaresTaskTools && telemetry.tasksCreated === 0) {
    findings.push(finding('RUN-TASK-NONE', 'critical', 'Task tools granted, no tasks created',
      'The setup grants a `Task*` tool and the run created zero tasks. This is the most common declared-versus-actual gap there is: the grant is present, the instruction to use it is not, and multi-phase work silently loses its place whenever the session compacts.', 'runtime'))
  }

  if (declared.phases.length >= 2 && telemetry.phaseSequence.length >= 2) {
    const declaredKeys = declared.phases.map((phase) => phase.split(/\s+/)[0])
    const actualKeys = telemetry.phaseSequence.map((phase) => String(phase).split(/\s+/)[0])
    const seen = actualKeys.filter((key) => declaredKeys.includes(key))
    const expected = declaredKeys.filter((key) => seen.includes(key))
    if (seen.join('>') !== expected.join('>')) {
      findings.push(finding('RUN-PHASE-ORDER', 'major', 'Phases ran out of declared order',
        `Declared order was ${expected.join(' then ')}. The run went ${seen.join(' then ')}. Either a gate is not enforced or the declared order is not the real one, and both are worth knowing before someone relies on the sequence.`, 'runtime'))
    }
  }

  telemetry.errors.forEach((error, index) => {
    findings.push(finding(`RUN-ERROR-${String(index).padStart(3, '0')}`, 'critical', 'Unhandled runtime error', error, 'runtime'))
  })

  return findings
}
