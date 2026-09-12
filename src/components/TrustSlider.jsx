const levels = [
  { id: 'low', label: 'Low', detail: 'Paste only · memory only' },
  { id: 'medium', label: 'Medium', detail: 'Files · manual state' },
  { id: 'high', label: 'High', detail: 'Folder access · persistence' }
]

export function TrustSlider({ value, onChange, highAvailable }) {
  return (
    <fieldset className="trust-control">
      <legend><span>Trust level</span><strong>{levels.find((level) => level.id === value)?.label}</strong></legend>
      <div className="trust-track">
        {levels.map((level, index) => {
          const disabled = level.id === 'high' && !highAvailable
          return (
            <label className={`${value === level.id ? 'selected' : ''} ${disabled ? 'disabled' : ''}`} key={level.id}>
              <input type="radio" name="trust" value={level.id} checked={value === level.id} disabled={disabled} onChange={() => onChange(level.id)} />
              <span className="trust-dot">{index + 1}</span>
              <span><b>{level.label}</b><small>{disabled ? 'Unavailable here' : level.detail}</small></span>
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
