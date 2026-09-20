import { streamText } from 'ai'
import { headers } from 'next/headers'
import { auth } from '@/lib/auth'

export async function POST(request: Request) {
  const session = await auth.api.getSession({ headers: await headers() })
  if (!session?.user) return new Response('Unauthorized', { status: 401 })
  const body = await request.json() as { message?: string }
  const message = body.message?.trim()
  if (!message || message.length > 8000) return new Response('Invalid message', { status: 400 })
  const result = streamText({ model: 'anthropic/claude-sonnet-4.5', system: `You are Anju AI, a calm, capable personal assistant. Address the user as ${session.user.name}. Be concise but useful. You can help plan, explain, write, reason, and organize. Be honest about limitations.`, prompt: message })
  return result.toTextStreamResponse()
}
