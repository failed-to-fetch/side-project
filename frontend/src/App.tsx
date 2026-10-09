// import { Button } from '@/components/ui/button'
import AuthPage from "./components/AuthPage";

import { useState } from 'react'

import { signIn, type User } from '@/lib/auth'
import type { SignInCredentials } from '@/components/sign-in-card'
import LoginPage from '@/pages/login'

function App() {
  const [user, setUser] = useState<User | null>(null)

  async function handleSignIn(credentials: SignInCredentials) {
    setUser(await signIn(credentials))
  }

  if (user) {
    return (
      <AuthPage />
      <div className="flex min-h-svh items-center justify-center">
        <p className="text-sm">Signed in as {user.email}</p>
      </div>
    )
  }

  return <LoginPage onSignIn={handleSignIn} />
}

export default App
