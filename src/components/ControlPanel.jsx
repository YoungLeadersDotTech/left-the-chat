import { Icon } from './Icon'
import { useStudio } from '../state/StudioContext'

function RangeControl({ label, value, min, max, step, onChange, hint }) {
  const progress = ((value - min) / (max - min)) * 100
  return (
    <label className="range-control">
      <span className="control-heading"><span>{label}</span><output>{value}</output></span>
      <input
        type="range"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
        style={{ '--range-progress': `${progress}%` }}
      />
      <span className="control-hint">{hint}</span>
    </label>
  )
}

function Switch({ checked, onChange, label }) {
  return (
    <button className="switch-row" type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}>
      <span>{label}</span>
      <span className={`switch ${checked ? 'switch-on' : ''}`}><span /></span>
    </button>
  )
}

export function ControlPanel() {
  const { parameters, setParameters } = useStudio()
  const update = (key, value) => setParameters((current) => ({ ...current, [key]: value }))
  const reset = () => setParameters((current) => ({ ...current, temperature: 0.7, topP: 1, maxTokens: 1024, stream: true }))

  return (
    <aside className="control-panel" aria-label="Model controls">
      <div className="panel-title">
        <div><p className="eyebrow">Live controls</p><h2>Parameters</h2></div>
        <button type="button" onClick={reset} aria-label="Reset parameters"><Icon name="reset" size={16} /></button>
      </div>

      <label className="select-control">
        <span>Model</span>
        <select value={parameters.model} onChange={(event) => update('model', event.target.value)}>
          <option value="studio-small">Studio Small</option>
          <option value="studio-reasoning">Studio Reasoning</option>
          <option value="studio-fast">Studio Fast</option>
        </select>
      </label>

      <div className="control-group">
        <RangeControl label="Temperature" value={parameters.temperature} min={0} max={2} step={0.1} onChange={(value) => update('temperature', value)} hint="Higher values explore more varied responses." />
        <RangeControl label="Top P" value={parameters.topP} min={0} max={1} step={0.05} onChange={(value) => update('topP', value)} hint="Limits the token pool by probability." />
        <RangeControl label="Max tokens" value={parameters.maxTokens} min={128} max={4096} step={128} onChange={(value) => update('maxTokens', value)} hint="Caps the length of the model output." />
      </div>

      <div className="control-section">
        <Switch label="Stream response" checked={parameters.stream} onChange={(value) => update('stream', value)} />
      </div>

      <label className="prompt-control">
        <span>System prompt</span>
        <textarea rows="4" value={parameters.systemPrompt} onChange={(event) => update('systemPrompt', event.target.value)} />
      </label>

      <div className="run-meta">
        <span><i className="status-dot" /> Mock transport</span>
        <code>0 tokens · $0.000</code>
      </div>
    </aside>
  )
}
