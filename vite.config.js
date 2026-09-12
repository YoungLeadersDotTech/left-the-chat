import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

function readBody(request) {
  return new Promise((resolve, reject) => {
    let body = ''
    request.on('data', (chunk) => { body += chunk })
    request.on('end', () => resolve(body))
    request.on('error', reject)
  })
}

function aiProxy(env) {
  return {
    name: 'ai-dev-proxy',
    configureServer(server) {
      server.middlewares.use('/api/chat', async (request, response) => {
        response.setHeader('Content-Type', 'application/x-ndjson; charset=utf-8')
        response.setHeader('Cache-Control', 'no-cache')

        try {
          const payload = JSON.parse((await readBody(request)) || '{}')
          const apiKey = env.OPENAI_API_KEY

          if (!apiKey) {
            const prompt = payload.messages?.at(-1)?.content || 'your idea'
            const mock = `Mock mode is active. I can already stream through the shared adapter and respond to “${prompt.slice(0, 80)}”. Add a server-side key when you are ready to connect a model.`
            for (const word of mock.split(' ')) {
              response.write(`${JSON.stringify({ delta: `${word} `, mode: 'mock' })}\n`)
              await new Promise((resolve) => setTimeout(resolve, 34))
            }
            response.end(`${JSON.stringify({ done: true, mode: 'mock' })}\n`)
            return
          }

          const upstream = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${apiKey}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              model: env.OPENAI_MODEL || 'gpt-4o-mini',
              messages: payload.messages || [],
              temperature: payload.parameters?.temperature ?? 0.7,
              top_p: payload.parameters?.topP ?? 1,
              stream: false
            })
          })

          if (!upstream.ok) throw new Error(`Model request failed (${upstream.status})`)
          const data = await upstream.json()
          response.end(`${JSON.stringify({ delta: data.choices?.[0]?.message?.content || '', done: true, mode: 'live' })}\n`)
        } catch (error) {
          response.statusCode = 500
          response.end(`${JSON.stringify({ error: error.message || 'Request failed' })}\n`)
        }
      })
    }
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react(), aiProxy(env)],
    server: { port: 5173 }
  }
})
