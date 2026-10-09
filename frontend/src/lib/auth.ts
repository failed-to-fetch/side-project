import type { SignInCredentials } from '@/components/sign-in-card'

export interface User {
  id: number
  email: string
  created_at: string
  updated_at: string
}

// TODO: replace with a real call to POST /auth/login once the backend exists.
export async function signIn({ email }: SignInCredentials): Promise<User> {
  await new Promise((resolve) => setTimeout(resolve, 500))

  const now = new Date().toISOString()
  return { id: 1, email, created_at: now, updated_at: now }
}
