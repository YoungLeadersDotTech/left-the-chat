import { useEffect, useMemo, useState } from 'react'
import { unzipSync, strFromU8 } from 'fflate'
import { Icon } from './components/Icon'
import { TrustSlider } from './components/TrustSlider'
import { Findings } from './components/Findings'
import { buildPromptA, buildPromptB, enrichAudit, inspectSetup } from './lib/audit'
import { downloadJson, sha256 } from './lib/deterministic'
import { parseTelemetry } from './lib/parsers'

const emptySession = { setupFiles: [], telemetry: '', parser: 'claude-code', baseline: null }
const pipelineSteps = [
  { label: 'Your prompt', detail: 'Add instructions and configuration' },
  { label: 'Copy the probe', detail: 'Run a generated test in your agent' },
  { label: 'Paste what came back', detail: 'Bring the runtime evidence back' },
  { label: 'Copy the fix', detail: 'Act on findings and measure again' }
]
const EXAMPLE_PROMPT = 'Review pull requests and flag risky changes before merge: anything touching auth, payments, or database migrations. Summarize each finding in one line with the file and reason.'
const MIN_MEANINGFUL_LENGTH = 40
const SINGLE_FILE_ACCEPT = '.md,.mdx,.markdown,.txt,text/plain,text/markdown'
function Metric({ label, value, delta }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong>{delta !== undefined ? <em className={delta <= 0 ? 'good' : 'bad'}>{delta > 0 ? '+' : ''}{delta}%</em> : null}</div>
}

export default function App() {
  const [theme, setTheme] = useState('dark')
  const [trust, setTrust] = useState('low')
  const [session, setSession] = useState(emptySession)
  const [report, setReport] = useState(null)
  const [hash, setHash] = useState('')
  const [copied, setCopied] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const standaloneFile = location.protocol === 'file:'
  const directoryPickerSupported = typeof window.showDirectoryPicker === 'function'
  const highAvailable = directoryPickerSupported && !standaloneFile

  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])
  useEffect(() => {
    if (trust !== 'high') return
    try {
      const stored = localStorage.getItem('left-the-chat-session')
      if (stored) setSession(JSON.parse(stored))
    } catch { /* unavailable or invalid local data stays ignored */ }
  }, [trust])
  useEffect(() => {
    if (trust !== 'high') return
    try { localStorage.setItem('left-the-chat-session', JSON.stringify(session)) } catch { /* manual export remains available */ }
  }, [session, trust])
  useEffect(() => {
    const context = document.modelContext
    if (!context?.registerTool) return undefined
    const lifecycle = new AbortController()
    try {
      Promise.resolve(context.registerTool({
        name: 'run_deterministic_audit',
        title: 'Run deterministic audit',
        description: 'Audit pasted agent setup text against runtime telemetry and display the resulting findings.',
        inputSchema: {
          type: 'object',
          properties: {
            setupText: { type: 'string' },
            telemetry: { type: 'string' },
            parser: { type: 'string', enum: ['auto', 'claude-code', 'generic'] }
          },
          required: ['setupText', 'telemetry'],
          additionalProperties: false
        },
        annotations: { readOnlyHint: false, untrustedContentHint: true },
        async execute(input) {
          if (typeof input?.setupText !== 'string' || typeof input?.telemetry !== 'string') throw new Error('setupText and telemetry must be strings.')
          const parser = input.parser || 'auto'
          const files = input.setupText ? [{ name: 'agent-provided-setup.txt', content: input.setupText }] : []
          const next = enrichAudit(inspectSetup(files), parseTelemetry(input.telemetry, parser))
          const nextHash = await sha256(next)
          setTrust('low')
          setSession({ ...emptySession, setupFiles: files, telemetry: input.telemetry, parser })
          setReport(next)
          setHash(nextHash)
          return { hash: nextHash, criticalCount: next.metrics.criticalCount, findingCount: next.metrics.findingCount }
        }
      }, { signal: lifecycle.signal })).catch(() => {})
    } catch { return undefined }
    return () => lifecycle.abort()
  }, [])

  const staticAudit = useMemo(() => inspectSetup(session.setupFiles), [session.setupFiles])
  const promptA = useMemo(() => buildPromptA(staticAudit), [staticAudit])
  const totalInputLength = session.setupFiles.reduce((sum, file) => sum + (file.content?.length || 0), 0)
  const hasMeaningfulInput = totalInputLength >= MIN_MEANINGFUL_LENGTH
  // Findings appear on drop, not on click. The static half needs no telemetry, and showing it
  // immediately is the moment the page proves it did something without uploading anything. Below
  // the meaningful-input floor, showing an empty "0 findings" report reads as a bug rather than an
  // honest "nothing to check yet" - the nudge in Findings.jsx covers that case instead.
  const shownReport = report || (staticAudit.files.length && hasMeaningfulInput
    ? { ...staticAudit, findings: staticAudit.findings, metrics: null, preliminary: true }
    : null)
  const promptB = report ? buildPromptB(report) : ''
  const criticalCount = report?.metrics.criticalCount || 0

  async function runAudit() {
    const telemetry = parseTelemetry(session.telemetry, session.parser)
    const next = enrichAudit(staticAudit, telemetry)
    setReport(next)
    setHash(await sha256(next))
    // T-45: an unset baseline reads "Not set" on the Closed metric, the one number on
    // screen that looks broken on a first run. Auto-set it so every run after the first
    // has something real to compare against; the button still lets you reset it later.
    setSession((current) => current.baseline ? current : { ...current, baseline: next })
  }

  async function addFiles(fileList) {
    const files = []
    for (const file of fileList) {
      if (file.name.toLowerCase().endsWith('.zip')) {
        const entries = unzipSync(new Uint8Array(await file.arrayBuffer()))
        for (const [name, bytes] of Object.entries(entries).sort(([a], [b]) => a.localeCompare(b))) {
          if (!name.endsWith('/')) files.push({ name, content: strFromU8(bytes) })
        }
      } else files.push({ name: file.webkitRelativePath || file.name, content: await file.text() })
    }
    setSession((current) => {
      const merged = new Map(current.setupFiles.map((file) => [file.name, file]))
      files.forEach((file) => merged.set(file.name, file))
      return { ...current, setupFiles: [...merged.values()].sort((a, b) => a.name.localeCompare(b.name)) }
    })
  }

  // Low trust is one input, not a file pile: pasted text, or one dropped file, never both at
  // once and never a zip or folder. Multi-file/folder/zip only exists from step 02 onward
  // (trust !== 'low'), where addFiles below still handles the full pile.
  function updatePastedSetup(content) {
    setSession((current) => ({ ...current, setupFiles: content ? [{ name: 'pasted-setup.txt', content }] : [] }))
  }

  async function addSingleFile(file) {
    if (!file) return
    const content = await file.text()
    setSession((current) => ({ ...current, setupFiles: [{ name: file.name, content }] }))
  }

  function dropSingleSetupFile(event) {
    event.preventDefault()
    setDragActive(false)
    addSingleFile(event.dataTransfer.files[0])
  }

  function dropSetupFiles(event) {
    event.preventDefault()
    setDragActive(false)
    if (event.dataTransfer.files.length) addFiles(event.dataTransfer.files)
  }

  async function pickDirectory() {
    if (!highAvailable) return
    const handle = await window.showDirectoryPicker()
    const files = []
    async function walk(directory, prefix = '') {
      for await (const [name, entry] of directory.entries()) {
        if (entry.kind === 'directory') await walk(entry, `${prefix}${name}/`)
        else files.push({ name: `${prefix}${name}`, content: await (await entry.getFile()).text() })
      }
    }
    await walk(handle)
    setSession((current) => ({ ...current, setupFiles: files.sort((a, b) => a.name.localeCompare(b.name)) }))
  }

  // D-23: a trust downgrade must not silently discard state. Confirm first, name
  // what is lost, offer the export on the step where the data can still be saved
  // (High -> Medium can hold a session file; Low cannot). Clear localStorage on
  // the way out of High regardless of destination, so High -> Medium -> refresh
  // does not silently restore data Medium claims not to persist.
  const TRUST_RANK = { low: 0, medium: 1, high: 2 }

  function changeTrust(next) {
    const isDowngrade = TRUST_RANK[next] < TRUST_RANK[trust]
    const hasState = session.setupFiles.length > 0 || report !== null

    if (isDowngrade && trust === 'high' && hasState) {
      const wantsExport = window.confirm(
        `Leaving High trust stops saving your session in this browser (${session.setupFiles.length} file(s)` +
        `${report ? ', the current report' : ''}). Export it as a file first?`
      )
      if (wantsExport) downloadJson('left-the-chat-session.json', { ...session, report, hash })
    }

    if (next === 'low' && isDowngrade && hasState) {
      const proceed = window.confirm(
        `Switching to Low trust clears ${session.setupFiles.length} file(s)` +
        `${report ? ' and the current report' : ''} from memory. Continue?`
      )
      if (!proceed) return
    }

    if (trust === 'high' && next !== 'high') localStorage.removeItem('left-the-chat-session')

    setTrust(next)
    if (next === 'low') { setSession(emptySession); setReport(null); setHash('') }
  }

  async function copy(value, id) {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(value)
    else {
      const helper = document.createElement('textarea')
      helper.value = value
      helper.style.position = 'fixed'
      helper.style.opacity = '0'
      document.body.appendChild(helper)
      helper.select()
      document.execCommand('copy')
      helper.remove()
    }
    setCopied(id)
    setTimeout(() => setCopied(''), 1400)
  }

  function importSession(file) {
    file.text().then((text) => {
      const value = JSON.parse(text)
      setSession({ ...emptySession, ...value })
      setReport(value.report || null)
      setHash(value.hash || '')
    })
  }

  const baseline = session.baseline
  const percent = (now, before) => before ? Math.round(((now - before) / before) * 100) : 0

  return (
    <div className="audit-app">
      <header className="topbar">
        <div className="brand-mark"><span className="brand-icon"><Icon name="spark" /></span><span>left the chat</span><i>LOCAL</i></div>
        <div className="privacy-mark"><span /> No data leaves this browser</div>
        <button className="icon-button" type="button" onClick={() => setTheme((value) => value === 'dark' ? 'light' : 'dark')} aria-label="Toggle theme"><Icon name={theme === 'dark' ? 'sun' : 'moon'} /></button>
      </header>

      <main>
        <section className="intro-row">
          <div><p className="eyebrow">Deterministic agent diagnostics</p><h1>Your agent says one thing.<br /><span>Measure what it does.</span></h1></div>
          <div className="intro-copy">
            <p>Left the Chat compares your agent’s setup with evidence from a real run. Add the configuration, follow the generated probe, then bring the telemetry back to get specific findings and a reusable fix prompt.</p>
            <div className="hero-points"><span>Runs locally</span><span>No API key</span><span>Reproducible results</span></div>
          </div>
        </section>

        <TrustSlider value={trust} onChange={changeTrust} />

        {trust === 'high' && !highAvailable ? (
          <section className="local-mode-notice">
            <div className="local-mode-copy">
              <p className="eyebrow">High trust compatibility mode</p>
              <h2>{standaloneFile ? 'Start local mode for persistent folder access' : 'Use Chrome or Edge for persistent folder access'}</h2>
              <p>{standaloneFile ? 'High is still selected, and you can use manual files and folders below. Browsers only allow a reusable folder connection from a trusted local address. The npm command starts that address; it does not add a backend or upload your files.' : 'This browser does not provide the folder permission used by High trust. Manual file and folder selection still works, or open the app in a current desktop version of Chrome or Edge.'}</p>
            </div>
            {standaloneFile ? <div className="local-setup">
              <p className="install-note-easiest">Easiest: open <a href="https://tools.youngleaders.tech/prompt-auditor" target="_blank" rel="noreferrer">tools.youngleaders.tech/prompt-auditor</a> - same file, nothing to install.</p>
              <div><span>1</span><div><strong>Check Node.js and npm</strong><p>Open Terminal on macOS or PowerShell on Windows, then run:</p><pre>node --version{`\n`}npm --version</pre><button type="button" onClick={() => copy('node --version\nnpm --version', 'npm-check')}><Icon name={copied === 'npm-check' ? 'check' : 'copy'} size={14} />{copied === 'npm-check' ? 'Copied' : 'Copy check commands'}</button></div></div>
              <div><span>2</span><div><strong>Start the local website</strong><p>In the unzipped repository folder, run:</p><pre>npm install{`\n`}npm run dev</pre><button type="button" onClick={() => copy('npm install\nnpm run dev', 'npm-run')}><Icon name={copied === 'npm-run' ? 'check' : 'copy'} size={14} />{copied === 'npm-run' ? 'Copied' : 'Copy run commands'}</button></div></div>
              <p className="install-note">If either check command is missing, install the current <a href="https://nodejs.org/en/download" target="_blank" rel="noreferrer">Node.js LTS release</a>. npm is included with Node.js. Then open the localhost address printed in the terminal.</p>
            </div> : null}
          </section>
        ) : trust === 'high' ? (
          <section className="local-mode-ready"><span /><div><strong>Persistent folder access is ready</strong><p>This page is running from a trusted local address. Files remain on this computer.</p></div></section>
        ) : null}

        <div className="pipeline-nav" aria-label="Audit pipeline">
          {pipelineSteps.map((step, index) => <div className="pipeline-step" key={step.label}><span>0{index + 1}</span><div><b>{step.label}</b><small>{step.detail}</small></div></div>)}
        </div>

        <p className="workbench-tie">One audit, in two halves - what you write on the left becomes the findings on the right.</p>

        <section className="workbench">
          <div className="input-column">
            <section className="panel ingest-panel">
              <div className="panel-heading"><div><span>01</span><div><h2>Your prompt</h2><p>{trust === 'low' ? 'Paste it, or drop one file. Nothing is stored.' : 'Drop configuration files or choose a folder.'}</p></div></div><code>{session.setupFiles.length} files</code></div>
              {trust === 'low' ? <textarea className="large-input" placeholder="Paste AGENTS.md, settings JSON, or agent instructions…" value={session.setupFiles.find((file) => file.name === 'pasted-setup.txt')?.content || ''} onChange={(event) => updatePastedSetup(event.target.value)} /> : null}
              {trust === 'low' ? (
                <label
                  className={`file-drop file-drop-compact ${dragActive ? 'drag-active' : ''}`}
                  onDragEnter={(event) => { event.preventDefault(); setDragActive(true) }}
                  onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; setDragActive(true) }}
                  onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragActive(false) }}
                  onDrop={dropSingleSetupFile}
                >
                  <input type="file" accept={SINGLE_FILE_ACCEPT} onChange={(event) => addSingleFile(event.target.files[0])} />
                  <Icon name="plus" /><strong>Or drop one file here</strong><span>A single .md or text file. A whole folder or ZIP goes in step 02.</span>
                </label>
              ) : (
                <label
                  className={`file-drop ${dragActive ? 'drag-active' : ''}`}
                  onDragEnter={(event) => { event.preventDefault(); setDragActive(true) }}
                  onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = 'copy'; setDragActive(true) }}
                  onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setDragActive(false) }}
                  onDrop={dropSetupFiles}
                >
                  <input type="file" multiple onChange={(event) => addFiles(event.target.files)} />
                  <Icon name="plus" /><strong>Drop setup files here, or choose files</strong><span>Supports individual files and ZIP archives. Everything is processed locally.</span>
                </label>
              )}
              {trust !== 'low' ? <label className="secondary-button folder-input"><Icon name="folder" /> Choose folder<input type="file" multiple webkitdirectory="" onChange={(event) => addFiles(event.target.files)} /></label> : null}
              {trust === 'high' && highAvailable ? <button className="secondary-button" type="button" onClick={pickDirectory}><Icon name="folder" /> Choose persistent folder</button> : null}
              {session.setupFiles.length ? <div className="file-list">{session.setupFiles.slice(0, 4).map((file) => <span key={file.name}>{file.name}</span>)}{session.setupFiles.length > 4 ? <span>+{session.setupFiles.length - 4} more</span> : null}</div> : null}
            </section>

            <section className="panel prompt-panel">
              <div className="panel-heading"><div><span>02</span><div><h2>Copy the probe</h2><p>Copy this into the agent whose setup you are measuring.</p></div></div><button type="button" onClick={() => copy(promptA, 'a')}><Icon name={copied === 'a' ? 'check' : 'copy'} size={14} />{copied === 'a' ? 'Copied' : 'Copy'}</button></div>
              <div className="code-block">
                <pre>{promptA}</pre>
                <button type="button" className="inline-copy" aria-label="Copy Prompt A" onClick={() => copy(promptA, 'a-inline')}><Icon name={copied === 'a-inline' ? 'check' : 'copy'} size={14} /></button>
              </div>
              <p className="prompt-subnote">Stopping here is a valid outcome - the static findings alone are still a real report, not a dead end.</p>
            </section>

            <section className="panel telemetry-panel">
              <div className="panel-heading"><div><span>03</span><div><h2>Paste what came back</h2><p>Paste returned JSON or JSONL from a Claude Code session. Other formats are not yet supported - parked until we have seen real shapes.</p></div></div></div>
              <textarea className="large-input" placeholder='{"tools":["Read"],"errors":[],"metrics":{"durationMs":1240,"inputTokens":820,"outputTokens":210}}' value={session.telemetry} onChange={(event) => setSession((current) => ({ ...current, telemetry: event.target.value }))} />
              <button className="primary-button" type="button" onClick={runAudit}><Icon name="activity" /> Run deterministic audit</button>
            </section>

            {report ? (
              <section className="metrics-panel">
                <div className="metrics-grid">
                  <Metric label="Tokens" value={report.metrics.totalTokens.toLocaleString()} delta={baseline ? percent(report.metrics.totalTokens, baseline.metrics.totalTokens) : undefined} />
                  <Metric label="Duration" value={`${(report.metrics.durationMs / 1000).toFixed(2)}s`} delta={baseline ? percent(report.metrics.durationMs, baseline.metrics.durationMs) : undefined} />
                  <Metric label="Errors" value={report.metrics.errorCount} delta={baseline ? report.metrics.errorCount - baseline.metrics.errorCount : undefined} />
                  <Metric label="Closed" value={baseline ? Math.max(0, baseline.metrics.findingCount - report.metrics.findingCount) : 'Not set'} />
                </div>
                <p className="cost-note">Estimated cost ${report.metrics.estimatedCostUsd.toFixed(6)} · reference rates {report.pricingTable.version}</p>
                <button className="baseline-button" type="button" onClick={() => setSession((current) => ({ ...current, baseline: report }))}>Use this run as baseline</button>
              </section>
            ) : null}

            {report ? (
              <section className="fix-prompt">
                <div><span>04</span><h3>Copy the fix</h3><button type="button" onClick={() => copy(promptB, 'b')}><Icon name={copied === 'b' ? 'check' : 'copy'} size={14} />{copied === 'b' ? 'Copied' : 'Copy'}</button></div>
                <div className="code-block">
                  <pre>{promptB}</pre>
                  <button type="button" className="inline-copy" aria-label="Copy Prompt B" onClick={() => copy(promptB, 'b-inline')}><Icon name={copied === 'b-inline' ? 'check' : 'copy'} size={14} /></button>
                </div>
              </section>
            ) : null}
          </div>

          <aside className="report-column">
            <section className="report-head"><div><p className="eyebrow">Findings for your prompt</p><h2>{report ? `${criticalCount} critical ${criticalCount === 1 ? 'finding' : 'findings'}` : shownReport ? `${shownReport.findings.length} from the files alone` : hasMeaningfulInput ? 'Waiting for input' : 'Try the example below'}</h2></div>{hash ? <code title={hash}>SHA-256 · {hash.slice(0, 10)}</code> : null}</section>
            <Findings report={shownReport} showNudge={!shownReport && !hasMeaningfulInput} onUseExample={() => updatePastedSetup(EXAMPLE_PROMPT)} />
          </aside>
        </section>

        {trust !== 'low' ? <section className="session-actions"><div><h2>Portable session</h2><p>{trust === 'high' ? 'Changes are also saved in this browser.' : 'State stays portable only when you export it.'}</p></div><label className="secondary-button">Import JSON<input type="file" accept="application/json" onChange={(event) => event.target.files[0] && importSession(event.target.files[0])} /></label><button className="secondary-button" type="button" onClick={() => downloadJson('left-the-chat-session.json', { ...session, report, hash })}>Export JSON</button></section> : null}
      </main>
      <footer><span>Left the Chat · Audit engine v1</span><span>Offline-ready · Pricing table 2026-09-v1</span></footer>
    </div>
  )
}
