import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Anju AI | Private assistant',
  description: 'A private, voice-ready AI assistant with persistent memory.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>
}
