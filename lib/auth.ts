import { betterAuth } from 'better-auth'
import { Pool } from 'pg'

const origin = (value?: string) => value ? (value.startsWith('http') ? value : `https://${value}`) : undefined
const baseURL = origin(process.env.BETTER_AUTH_URL || process.env.VERCEL_PROJECT_PRODUCTION_URL || process.env.VERCEL_URL || process.env.V0_RUNTIME_URL)
const trustedOrigins = [
  'http://localhost:3000',
  ...[process.env.V0_RUNTIME_URL, process.env.V0_DEV_APP_URL, process.env.V0_BUILD_URL, process.env.V0_SANDBOX_URL, process.env.VERCEL_URL, process.env.VERCEL_PROJECT_PRODUCTION_URL].map(origin).filter((value): value is string => Boolean(value)),
]

export const auth = betterAuth({
  database: new Pool({ connectionString: process.env.DATABASE_URL }),
  baseURL,
  trustedOrigins,
  emailAndPassword: { enabled: true },
  advanced: process.env.NODE_ENV === 'development' ? { defaultCookieAttributes: { sameSite: 'none', secure: true } } : undefined,
})
