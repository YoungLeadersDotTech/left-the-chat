import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const StudioContext = createContext(null)

const initialMessages = [
  {
    id: 'welcome',
    role: 'assistant',
    content: 'Bring me a half-formed idea. We can make it useful together.'
  }
]

export function StudioProvider({ children }) {
  const [theme, setTheme] = useState(() => localStorage.getItem('studio-theme') || 'dark')
  const [messages, setMessages] = useState(initialMessages)
  const [parameters, setParameters] = useState({
    model: 'studio-small',
    temperature: 0.7,
    topP: 1,
    maxTokens: 1024,
    stream: true,
    systemPrompt: 'Be clear, curious, and concise.'
  })
  const [isStreaming, setIsStreaming] = useState(false)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('studio-theme', theme)
  }, [theme])

  useEffect(() => {
    const context = document.modelContext
    if (!context?.registerTool) return undefined
    const lifecycle = new AbortController()
    const clamp = (value, min, max) => Math.min(max, Math.max(min, Number(value)))

    try {
      Promise.resolve(context.registerTool({
        name: 'configure_model_parameters',
        title: 'Configure model parameters',
        description: 'Update the visible AI Studio temperature, top-p, and maximum output token controls.',
        inputSchema: {
          type: 'object',
          properties: {
            temperature: { type: 'number', minimum: 0, maximum: 2 },
            topP: { type: 'number', minimum: 0, maximum: 1 },
            maxTokens: { type: 'integer', minimum: 128, maximum: 4096 }
          },
          additionalProperties: false
        },
        annotations: { readOnlyHint: false, untrustedContentHint: false },
        execute(input) {
          if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Parameters must be an object.')
          const allowed = ['temperature', 'topP', 'maxTokens']
          if (Object.keys(input).some((key) => !allowed.includes(key))) throw new Error('Unknown parameter.')
          setParameters((current) => ({
            ...current,
            ...(input.temperature === undefined ? {} : { temperature: clamp(input.temperature, 0, 2) }),
            ...(input.topP === undefined ? {} : { topP: clamp(input.topP, 0, 1) }),
            ...(input.maxTokens === undefined ? {} : { maxTokens: Math.round(clamp(input.maxTokens, 128, 4096)) })
          }))
          return { updated: true, parameters: input }
        }
      }, { signal: lifecycle.signal })).catch(() => {})
    } catch {
      return undefined
    }
    return () => lifecycle.abort()
  }, [])

  const value = useMemo(() => ({
    theme,
    toggleTheme: () => setTheme((current) => current === 'dark' ? 'light' : 'dark'),
    messages,
    setMessages,
    parameters,
    setParameters,
    isStreaming,
    setIsStreaming
  }), [theme, messages, parameters, isStreaming])

  return <StudioContext.Provider value={value}>{children}</StudioContext.Provider>
}

export function useStudio() {
  const context = useContext(StudioContext)
  if (!context) throw new Error('useStudio must be used within StudioProvider')
  return context
}
