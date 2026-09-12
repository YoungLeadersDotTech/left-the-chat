import { NavLink, Route, Routes } from 'react-router-dom'
import { Icon } from './components/Icon'
import { StudioPage } from './pages/StudioPage'
import { useStudio } from './state/StudioContext'

function AppShell() {
  const { theme, toggleTheme } = useStudio()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark" aria-label="Left the Chat">
          <span className="brand-icon"><Icon name="spark" /></span>
          <span>left the chat</span>
        </div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <NavLink to="/" end><Icon name="message" /><span>Studio</span></NavLink>
          <NavLink to="/runs"><Icon name="activity" /><span>Runs</span></NavLink>
        </nav>
        <button className="sidebar-action" type="button" onClick={toggleTheme}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
          <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>
        </button>
      </aside>
      <main className="main-stage">
        <Routes>
          <Route path="/" element={<StudioPage />} />
          <Route path="/runs" element={<div className="empty-page"><p className="eyebrow">Run history</p><h1>Nothing has left the lab yet.</h1><p>Your model runs will collect here as the studio grows.</p></div>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return <AppShell />
}
