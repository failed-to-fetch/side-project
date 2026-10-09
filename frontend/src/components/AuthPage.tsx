import { useState } from "react";
import { authClient } from "../lib/auth-client";
import "./AuthPage.css";

type Provider = "github" | "gitlab" | "bitbucket";

export default function AuthPage() {
    const [mode, setMode] = useState<"signin" | "signup">("signin");
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState("");
    const [message, setMessage] = useState("");

    async function socialSignIn(provider: Provider) {
        setLoading(provider);
        setMessage("");

        try {
            await authClient.signIn.social({
                provider,
                callbackURL: "/",
            });
        } catch (error) {
            console.error(`${provider} sign-in failed:`, error);
            setMessage(
                error instanceof Error
                    ? `Could not start ${provider} sign-in: ${error.message}`
                    : `Could not start ${provider} sign-in. Check the browser console and OAuth configuration.`
            );
            setLoading("");
        }
    }

    async function submitEmail(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setLoading("email");
        setMessage("");

        try {
            const result =
                mode === "signup"
                    ? await authClient.signUp.email({
                        name,
                        email,
                        password,
                    })
                    : await authClient.signIn.email({
                        email,
                        password,
                    });

            if (result.error) {
                setMessage(result.error.message || "Authentication failed.");
            } else {
                setMessage(
                    mode === "signup"
                        ? "Account created successfully."
                        : "Signed in successfully!"
                );
            }
        } catch (error) {
            console.error("Email authentication failed:", error);

            setMessage(
                error instanceof Error
                    ? `Authentication request failed: ${error.message}`
                    : "Authentication request failed. Check the browser console and confirm the auth server is reachable at http://localhost:3001."
            );
        } finally {
            setLoading("");
        }
    }

    return (
        <main className="auth-shell">
            <header className="auth-header">
                <a className="brand" href="/">
                    <span className="brand-mark">&lt;/&gt;</span>
                    <span>SideProject</span>
                </a>
                <span className="header-caption">Developer workspace</span>
            </header>

            <section className="auth-layout">
                <div className="auth-intro">
                    <div className="eyebrow">
                        <span className="status-dot" />
                        YOUR WORKSPACE STARTS HERE
                    </div>

                    <h1>
                        Your projects.
                        <br />
                        <span>Your workflow.</span>
                    </h1>

                    <p className="intro-copy">
                        Bring your repositories together. Connect your accounts
                        and manage your projects from one place.
                    </p>

                    <div className="feature-list">
                        <div className="feature-item">
                            <span className="feature-icon">⌘</span>
                            <div>
                                <strong>One workspace</strong>
                                <p>Keep your development workflow organized.</p>
                            </div>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">↗</span>
                            <div>
                                <strong>Your providers</strong>
                                <p>Connect GitHub, GitLab and Bitbucket.</p>
                            </div>
                        </div>
                        <div className="feature-item">
                            <span className="feature-icon">◇</span>
                            <div>
                                <strong>Built for developers</strong>
                                <p>Spend more time building great things.</p>
                            </div>
                        </div>
                    </div>

                    <div className="intro-footer">
                        <span className="footer-line" />
                        A home for everything you're building.
                    </div>
                </div>

                <div className="auth-card">
                    <div className="card-symbol">&lt;/&gt;</div>

                    <h2>
                        {mode === "signin" ? "Welcome back" : "Create your account"}
                    </h2>
                    <p className="card-subtitle">
                        {mode === "signin"
                            ? "Sign in to continue to your workspace."
                            : "Get started with your developer workspace."}
                    </p>

                    <div className="auth-tabs">
                        <button
                            type="button"
                            className={mode === "signin" ? "active" : ""}
                            onClick={() => {
                                setMode("signin");
                                setMessage("");
                            }}
                        >
                            Sign in
                        </button>
                        <button
                            type="button"
                            className={mode === "signup" ? "active" : ""}
                            onClick={() => {
                                setMode("signup");
                                setMessage("");
                            }}
                        >
                            Create account
                        </button>
                    </div>

                    <div className="social-buttons">
                        <button
                            className="social-button github-button"
                            disabled={!!loading}
                            onClick={() => socialSignIn("github")}
                            type="button"
                        >
                            <span className="provider-symbol">◉</span>
                            {loading === "github" ? "Connecting..." : "Continue with GitHub"}
                        </button>

                        <button
                            className="social-button"
                            disabled={!!loading}
                            onClick={() => socialSignIn("gitlab")}
                            type="button"
                        >
                            <span className="provider-symbol gitlab-symbol">◆</span>
                            {loading === "gitlab" ? "Connecting..." : "Continue with GitLab"}
                        </button>

                        <button
                            className="social-button"
                            disabled={!!loading}
                            onClick={() => socialSignIn("bitbucket")}
                            type="button"
                        >
                            <span className="provider-symbol bitbucket-symbol">◈</span>
                            {loading === "bitbucket"
                                ? "Connecting..."
                                : "Continue with Bitbucket"}
                        </button>
                    </div>

                    <div className="divider-label">
                        <span />
                        <small>OR CONTINUE WITH EMAIL</small>
                        <span />
                    </div>

                    <form onSubmit={submitEmail} className="email-form">
                        {mode === "signup" && (
                            <label>
                                Full name
                                <input
                                    autoComplete="name"
                                    placeholder="Your name"
                                    value={name}
                                    onChange={(event) => setName(event.target.value)}
                                    required
                                />
                            </label>
                        )}

                        <label>
                            Email address
                            <input
                                type="email"
                                autoComplete="email"
                                placeholder="you@example.com"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                required
                            />
                        </label>

                        <label>
                            Password
                            <input
                                type="password"
                                autoComplete={
                                    mode === "signup" ? "new-password" : "current-password"
                                }
                                placeholder="At least 8 characters"
                                minLength={8}
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                required
                            />
                        </label>

                        {message && (
                            <div className="auth-message" role="status">
                                {message}
                            </div>
                        )}

                        <button
                            type="submit"
                            className="submit-button"
                            disabled={!!loading}
                        >
                            {loading === "email"
                                ? "Please wait..."
                                : mode === "signin"
                                    ? "Sign in to your account"
                                    : "Create your account"}
                            <span>→</span>
                        </button>
                    </form>

                    <p className="terms">
                        By continuing, you agree to our <a href="/terms">Terms</a> and{" "}
                        <a href="/privacy">Privacy Policy</a>.
                    </p>
                </div>
            </section>

            <footer className="page-footer">
                <span>© {new Date().getFullYear()} SideProject</span>
                <span>Made for people who build.</span>
            </footer>
        </main>
    );
}