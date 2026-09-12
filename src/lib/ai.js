export async function streamChat({ messages, parameters, onDelta }) {
  let response
  try {
    response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, parameters })
    })
  } catch {
    response = null
  }

  if (!response?.ok || !response.body || !response.headers.get('content-type')?.includes('ndjson')) {
    const prompt = messages.at(-1)?.content || 'your idea'
    const mock = `Mock mode is active. The studio received “${prompt.slice(0, 80)}” and your controls are wired up. Connect the server adapter to a model when you are ready.`
    for (const word of mock.split(' ')) {
      onDelta(`${word} `)
      await new Promise((resolve) => setTimeout(resolve, 28))
    }
    return { mode: 'mock' }
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let mode = 'mock'

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.trim()) continue
      const event = JSON.parse(line)
      if (event.error) throw new Error(event.error)
      mode = event.mode || mode
      if (event.delta) onDelta(event.delta)
    }
  }

  return { mode }
}
