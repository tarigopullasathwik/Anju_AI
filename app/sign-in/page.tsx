'use client'
import { FormEvent, useState } from 'react'
import { useRouter } from 'next/navigation'
import { authClient } from '@/lib/auth-client'

export default function SignIn() {
  const router = useRouter(); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [name,setName]=useState(''); const [signup,setSignup]=useState(false); const [error,setError]=useState(''); const [busy,setBusy]=useState(false)
  async function submit(e: FormEvent) { e.preventDefault(); setBusy(true); setError(''); const result = signup ? await authClient.signUp.email({ email, password, name }) : await authClient.signIn.email({ email, password }); setBusy(false); if (result.error) setError('That sign-in could not be completed. Check your details and try again.'); else { router.push('/'); router.refresh() } }
  return <main className="auth-page"><div className="auth-card"><div className="eyebrow">ANJU AI / PRIVATE ACCESS</div><h1>{signup ? 'Create your private workspace' : 'Welcome back, commander'}</h1><p>Secure conversations, persistent memory, and a voice-ready assistant.</p><form onSubmit={submit}>{signup && <input aria-label="Name" placeholder="Your name" value={name} onChange={e=>setName(e.target.value)} required />}<input aria-label="Email" type="email" placeholder="Email address" value={email} onChange={e=>setEmail(e.target.value)} required /><input aria-label="Password" type="password" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} minLength={8} required />{error && <div className="error">{error}</div>}<button className="primary-button" disabled={busy}>{busy ? 'Opening secure channel…' : signup ? 'Create workspace' : 'Enter workspace'}</button></form><button className="text-button" onClick={()=>setSignup(!signup)}>{signup ? 'Already have an account? Sign in' : 'New here? Create an account'}</button></div></main>
}
