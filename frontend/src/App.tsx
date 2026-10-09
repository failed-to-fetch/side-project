import { useCallback, useEffect, useState } from "react";
import { authClient } from "@/lib/auth-client";
import AuthPage from "@/pages/AuthPage";
import SuccessPage from "@/pages/success";

type Session = {
  user: {
    email: string;
    name: string;
  };
};

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshSession = useCallback(async () => {
    const { data, error } = await authClient.getSession();


    if (error) {
      console.error("Failed to get session:", error);
      return false;
    }

    console.log("Session returned by Better Auth:", data);
    setSession(data as Session | null);

    return !!data?.user;
  }, []);

  useEffect(() => {
    refreshSession().finally(() => setLoading(false));
  }, [refreshSession]);

  async function handleSignOut() {
    const { error } = await authClient.signOut();

    if (error) {
      console.error("Sign-out failed:", error);
      return;
    }

    setSession(null);

  }

  if (loading) {
    return (<main className="flex min-h-svh items-center justify-center">
      Checking your session... </main>
    );
  }

  if (session?.user) {
    return (<SuccessPage
      email={session.user.email}
      onSignOut={handleSignOut}
    />
    );
  }

  return (
    <AuthPage
      onSignedIn={async () => {
        const success = await refreshSession();

        if (!success) {
          console.error(
            "Sign-in succeeded, but no session was returned. Check the auth cookie and browser Network tab."
          );
        }
      }}
    />

  );
}
