const levels = [
  { id: 'low', label: 'Low', title: 'One-off inspection', detail: 'Paste or drop files. Clears when the page closes.' },
  { id: 'medium', label: 'Medium', title: 'Portable review', detail: 'Add files or folders. Export the session to keep it.' },
  { id: 'high', label: 'High', title: 'Persistent workspace', detail: 'Save in this browser and reconnect to a folder.' }
]

export function TrustSlider({ value, onChange }) {
  const selectedIndex = levels.findIndex((level) => level.id === value)
  const progress = selectedIndex * 50

  function selectIndex(index) {
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
        {levels.map((level, index) => (
            <button className={value === level.id ? 'selected' : ''} key={level.id} type="button" tabIndex="-1" onClick={() => selectIndex(index)}>
              <span className="trust-dot">{index + 1}</span>
              <span className="trust-copy"><b>{level.label}</b><small>{level.title}</small><span className="trust-description">{level.detail}</span></span>
            </button>
        ))}
        </div>
      </div>
    </fieldset>
  )
}
