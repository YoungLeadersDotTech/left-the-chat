function Finding({ item }) {
  return (
    <article className={`finding finding-${item.severity}`}>
      <div><span>{item.id}</span><em>{item.source}</em></div>
      <h3>{item.title}</h3>
      <p>{item.detail}</p>
    </article>
  )
}

export function Findings({ report }) {
  // Critical and major are the structural and declared-versus-actual findings, which are the
  // reason this is an auditor rather than a linter. Only style and prose collapse (decision D-10).
  const critical = report?.findings.filter((item) => item.severity === 'critical' || item.severity === 'major') || []
  const minor = report?.findings.filter((item) => item.severity !== 'critical' && item.severity !== 'major') || []
  if (!report) return <div className="report-empty"><span>00</span><p>Your deterministic report will appear here.</p></div>
  return (
    <div className="findings-list">
      {critical.length ? critical.map((item) => <Finding item={item} key={item.id} />) : <div className="all-clear">No critical discrepancies detected.</div>}
      {minor.length ? <details><summary>Also found <span>{minor.length}</span></summary>{minor.map((item) => <Finding item={item} key={item.id} />)}</details> : null}
    </div>
  )
}
