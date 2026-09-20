import { headers } from 'next/headers'
import { redirect } from 'next/navigation'
import { auth } from '@/lib/auth'
import { AssistantWorkspace } from '@/components/assistant-workspace'

export default async function Home() {
  const session = await auth.api.getSession({ headers: await headers() })
  if (!session?.user) redirect('/sign-in')
  return <AssistantWorkspace user={{ name: session.user.name, email: session.user.email }} />
}
