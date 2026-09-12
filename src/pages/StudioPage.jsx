import { useState } from 'react'
import { Icon } from '../components/Icon'
import { ControlPanel } from '../components/ControlPanel'
import { streamChat } from '../lib/ai'
import { useStudio } from '../state/StudioContext'

export function StudioPage() {
  const { messages, setMessages, parameters, isStreaming, setIsStreaming } = useStudio()
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    const content = draft.trim()
    if (!content || isStreaming) return

    const userMessage = { id: crypto.randomUUID(), role: 'user', content }
    const assistantId = crypto.randomUUID()
    const nextMessages = [...messages, userMessage]
    setMessages([...nextMessages, { id: assistantId, role: 'assistant', content: '' }])
    setDraft('')
    setError('')
    setIsStreaming(true)

    try {
      await streamChat({
        messages: nextMessages.map(({ role, content: text }) => ({ role, content: text })),
        parameters,
        onDelta: (delta) => setMessages((current) => current.map((message) =>
          message.id === assistantId ? { ...message, content: message.content + delta } : message
        ))
      })
    } catch (requestError) {
      setError(requestError.message)
      setMessages((current) => current.filter((message) => message.id !== assistantId))
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <section className="studio-page">
      <header className="studio-header">
        <div>
          <p className="eyebrow">Workspace / Untitled experiment</p>
          <h1>Conversation studio</h1>
        </div>
        <div className="connection-pill"><span /> Mock model</div>
      </header>

      <div className="workspace-grid">
        <section className="chat-panel" aria-label="AI conversation">
          <div className="chat-toolbar">
            <div><span className="status-dot" /> Ready to explore</div>
            <button type="button" onClick={() => setMessages(messages.slice(0, 1))}><Icon name="reset" /> Clear</button>
          </div>
          <div className="message-list" aria-live="polite">
            {messages.map((message) => (
              <article className={`message message-${message.role}`} key={message.id}>
                <div className="avatar">{message.role === 'assistant' ? <Icon name="spark" size={15} /> : 'Y'}</div>
                <div>
                  <p className="message-label">{message.role === 'assistant' ? 'Studio' : 'You'}</p>
                  <p>{message.content}{isStreaming && message === messages.at(-1) ? <span className="cursor" /> : null}</p>
                </div>
              </article>
            ))}
          </div>
          <form className="composer" onSubmit={submit}>
            {error ? <p className="form-error">{error}</p> : null}
            <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask, test, or paste an idea…" rows="3" onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(event) }
            }} />
            <div className="composer-footer">
              <button className="add-button" type="button" aria-label="Add context"><Icon name="plus" /></button>
              <span>Enter to send · Shift + Enter for a new line</span>
              <button className="send-button" type="submit" disabled={!draft.trim() || isStreaming} aria-label="Send message"><Icon name="send" /></button>
            </div>
          </form>
        </section>

        <ControlPanel />
      </div>
    </section>
  )
}
