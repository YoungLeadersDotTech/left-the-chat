function Finding({ item }) {
  return (
    <article className={`finding finding-${item.severity}`}>
      <div><span>{item.id}</span>{item.line ? <b className="finding-line">line {item.line}</b> : null}<em>{item.source}</em></div>
      <h3>{item.title}</h3>
      <p>{item.detail}</p>
    </article>
  )
}

export function Findings({ report, showNudge, onUseExample }) {
  // Critical and major are the structural and declared-versus-actual findings, which are the
  // reason this is an auditor rather than a linter. Only style and prose collapse (decision D-10).
  const critical = report?.findings.filter((item) => item.severity === 'critical' || item.severity === 'major') || []
  const minor = report?.findings.filter((item) => item.severity !== 'critical' && item.severity !== 'major') || []
  if (!report) {
    if (showNudge) {
      return (
        <div className="report-empty report-nudge">
          <p>Paste at least a sentence to see findings.</p>
          <button type="button" className="example-prompt-button" onClick={onUseExample}>
            Try an example: "Review pull requests and flag risky changes before merge."
          </button>
        </div>
      )
    }
    return <div className="report-empty"><span>00</span><p>Your deterministic report will appear here.</p></div>
  }
  return (
    <div className="findings-list">
      {critical.length ? critical.map((item) => <Finding item={item} key={item.id} />) : <div className="all-clear">No critical discrepancies detected.</div>}
      {minor.length ? <details><summary>Also found <span>{minor.length}</span></summary>{minor.map((item) => <Finding item={item} key={item.id} />)}</details> : null}
    </div>
  )
}
