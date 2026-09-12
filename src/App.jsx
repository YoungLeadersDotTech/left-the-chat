import { useEffect, useMemo, useState } from 'react'
import { unzipSync, strFromU8 } from 'fflate'
import { Icon } from './components/Icon'
import { TrustSlider } from './components/TrustSlider'
import { Findings } from './components/Findings'
import { buildPromptA, buildPromptB, enrichAudit, inspectSetup } from './lib/audit'
import { downloadJson, sha256 } from './lib/deterministic'
import { parseTelemetry } from './lib/parsers'

const emptySession = { setupFiles: [], telemetry: '', parser: 'auto', baseline: null }

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
  const [launchDir, setLaunchDir] = useState('')
  const highAvailable = typeof window.showDirectoryPicker === 'function' && location.protocol !== 'file:'

  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])
  useEffect(() => {
    if (trust !== 'high') return
    const stored = localStorage.getItem('left-the-chat-session')
    if (stored) { try { setSession(JSON.parse(stored)) } catch { /* invalid local data stays ignored */ } }
  }, [trust])
  useEffect(() => {
    if (trust === 'high') localStorage.setItem('left-the-chat-session', JSON.stringify(session))
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
            parser: { type: 'string', enum: ['auto', 'claude-code', 'opencode'] }
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
  const promptB = report ? buildPromptB(report) : ''
  const criticalCount = report?.metrics.criticalCount || 0

  async function runAudit() {
    const telemetry = parseTelemetry(session.telemetry, session.parser)
    const next = enrichAudit(staticAudit, telemetry)
    setReport(next)
    setHash(await sha256(next))
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
    setSession((current) => ({ ...current, setupFiles: [...current.setupFiles, ...files].sort((a, b) => a.name.localeCompare(b.name)) }))
  }

  async function pickDirectory() {
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

  const logPath = launchDir ? `~/.claude/projects/${launchDir.replace(/[\\/.]/g, '-').replace(/^-+|-+$/g, '')}/` : 'Enter a launch directory to compute the log path.'
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
          <div><p className="eyebrow">Deterministic agent diagnostics</p><h1>Measure the setup.<br /><span>Close the loop.</span></h1></div>
          <p>Inspect agent configuration, compare declared access with real runtime behavior, and generate a reproducible fix prompt—all inside your browser.</p>
        </section>

        <TrustSlider value={trust} onChange={(level) => { setTrust(level); if (level === 'low') { setSession(emptySession); setReport(null); setHash('') } }} highAvailable={highAvailable} />

        <div className="pipeline-nav" aria-label="Audit pipeline">
          {['Setup', 'Probe', 'Telemetry', 'Fix & compare'].map((label, index) => <div key={label}><span>0{index + 1}</span><b>{label}</b></div>)}
        </div>

        <section className="workbench">
          <div className="input-column">
            <section className="panel ingest-panel">
              <div className="panel-heading"><div><span>01</span><div><h2>Setup input</h2><p>{trust === 'low' ? 'Paste configuration text. Nothing is stored.' : 'Add configuration files or a folder.'}</p></div></div><code>{session.setupFiles.length} files</code></div>
              {trust === 'low' ? (
                <textarea className="large-input" placeholder="Paste AGENTS.md, settings JSON, or agent instructions…" value={session.setupFiles[0]?.content || ''} onChange={(event) => setSession((current) => ({ ...current, setupFiles: event.target.value ? [{ name: 'pasted-setup.txt', content: event.target.value }] : [] }))} />
              ) : (
                <label className="file-drop">
                  <input type="file" multiple onChange={(event) => addFiles(event.target.files)} />
                  <Icon name="plus" /><strong>Choose a ZIP or setup files</strong><span>Files are processed locally and never uploaded.</span>
                </label>
              )}
              {trust !== 'low' ? <label className="secondary-button folder-input"><Icon name="folder" /> Choose folder<input type="file" multiple webkitdirectory="" onChange={(event) => addFiles(event.target.files)} /></label> : null}
              {trust === 'high' ? <button className="secondary-button" type="button" onClick={pickDirectory}><Icon name="folder" /> Choose persistent folder</button> : null}
              {session.setupFiles.length ? <div className="file-list">{session.setupFiles.slice(0, 4).map((file) => <span key={file.name}>{file.name}</span>)}{session.setupFiles.length > 4 ? <span>+{session.setupFiles.length - 4} more</span> : null}</div> : null}
            </section>

            <section className="panel prompt-panel">
              <div className="panel-heading"><div><span>02</span><div><h2>Prompt A · Probe</h2><p>Copy this into the agent whose setup you are measuring.</p></div></div><button type="button" onClick={() => copy(promptA, 'a')}>{copied === 'a' ? 'Copied' : 'Copy'}</button></div>
              <pre>{promptA}</pre>
            </section>

            <section className="panel telemetry-panel">
              <div className="panel-heading"><div><span>03</span><div><h2>Runtime telemetry</h2><p>Paste returned JSON or JSONL. Claude Code and OpenCode are normalized automatically.</p></div></div>
                <select value={session.parser} onChange={(event) => setSession((current) => ({ ...current, parser: event.target.value }))}><option value="auto">Auto detect</option><option value="claude-code">Claude Code</option><option value="opencode">OpenCode</option></select>
              </div>
              <textarea className="large-input" placeholder='{"tools":["Read"],"errors":[],"metrics":{"durationMs":1240,"inputTokens":820,"outputTokens":210}}' value={session.telemetry} onChange={(event) => setSession((current) => ({ ...current, telemetry: event.target.value }))} />
              {trust === 'low' ? <div className="path-helper"><input placeholder="Launch directory, e.g. ~/projects/my-project" value={launchDir} onChange={(event) => setLaunchDir(event.target.value)} /><code>{logPath}</code></div> : null}
              <button className="primary-button" type="button" onClick={runAudit}><Icon name="activity" /> Run deterministic audit</button>
            </section>
          </div>

          <aside className="report-column">
            <section className="report-head"><div><p className="eyebrow">Diagnostic report</p><h2>{report ? `${criticalCount} critical ${criticalCount === 1 ? 'finding' : 'findings'}` : 'Waiting for input'}</h2></div>{hash ? <code title={hash}>SHA-256 · {hash.slice(0, 10)}</code> : null}</section>
            <Findings report={report} />
            {report ? <>
              <div className="metrics-grid">
                <Metric label="Tokens" value={report.metrics.totalTokens.toLocaleString()} delta={baseline ? percent(report.metrics.totalTokens, baseline.metrics.totalTokens) : undefined} />
                <Metric label="Duration" value={`${(report.metrics.durationMs / 1000).toFixed(2)}s`} delta={baseline ? percent(report.metrics.durationMs, baseline.metrics.durationMs) : undefined} />
                <Metric label="Errors" value={report.metrics.errorCount} delta={baseline ? report.metrics.errorCount - baseline.metrics.errorCount : undefined} />
                <Metric label="Closed" value={baseline ? Math.max(0, baseline.metrics.findingCount - report.metrics.findingCount) : '—'} />
              </div>
              <p className="cost-note">Estimated cost ${report.metrics.estimatedCostUsd.toFixed(6)} · reference rates {report.pricingTable.version}</p>
              <section className="fix-prompt"><div><span>04</span><h3>Prompt B · Fix</h3><button type="button" onClick={() => copy(promptB, 'b')}>{copied === 'b' ? 'Copied' : 'Copy'}</button></div><pre>{promptB}</pre></section>
              <button className="baseline-button" type="button" onClick={() => setSession((current) => ({ ...current, baseline: report }))}>Use this run as baseline</button>
            </> : null}
          </aside>
        </section>

        {trust !== 'low' ? <section className="session-actions"><div><h2>Portable session</h2><p>{trust === 'high' ? 'Changes are also saved in this browser.' : 'State stays portable only when you export it.'}</p></div><label className="secondary-button">Import JSON<input type="file" accept="application/json" onChange={(event) => event.target.files[0] && importSession(event.target.files[0])} /></label><button className="secondary-button" type="button" onClick={() => downloadJson('left-the-chat-session.json', { ...session, report, hash })}>Export JSON</button></section> : null}
      </main>
      <footer><span>Left the Chat · Audit engine v1</span><span>Offline-ready · Pricing table 2026-09-v1</span></footer>
    </div>
  )
}
