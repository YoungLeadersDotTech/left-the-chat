const levels = [
  { id: 'low', label: 'Low', detail: 'Paste only · memory only' },
  { id: 'medium', label: 'Medium', detail: 'Files · manual state' },
  { id: 'high', label: 'High', detail: 'Folder access · persistence' }
]

export function TrustSlider({ value, onChange, highAvailable }) {
  const selectedIndex = levels.findIndex((level) => level.id === value)
  const progress = selectedIndex * 50

  function selectIndex(index) {
    if (index === 2 && !highAvailable) return
    onChange(levels[index].id)
  }

  return (
    <fieldset className="trust-control">
      <legend><span>Trust level</span><strong>{levels.find((level) => level.id === value)?.label}</strong></legend>
      <div className="trust-slider-shell">
        <input
          className="trust-range"
          type="range"
          min="0"
          max="2"
          step="1"
          value={selectedIndex}
          aria-label="Trust level"
          aria-valuetext={levels[selectedIndex].label}
          onChange={(event) => selectIndex(Number(event.target.value))}
          style={{ '--trust-progress': `${progress}%` }}
        />
        <div className="trust-track" aria-hidden="true">
        {levels.map((level, index) => {
          const disabled = level.id === 'high' && !highAvailable
          return (
            <button className={`${value === level.id ? 'selected' : ''} ${disabled ? 'disabled' : ''}`} key={level.id} type="button" tabIndex="-1" disabled={disabled} onClick={() => selectIndex(index)}>
              <span className="trust-dot">{index + 1}</span>
              <span><b>{level.label}</b><small>{disabled ? 'Needs a served page - this file is open from disk' : level.detail}</small></span>
            </button>
          )
        })}
        </div>
      </div>
      {!highAvailable ? <p className="trust-note">High works on the hosted version. There is no back end anywhere in this page - it is a browser API (showDirectoryPicker) that a file opened directly from disk cannot call.</p> : null}
    </fieldset>
  )
}
