type SuccessPageProps = {
    email: string;
    onSignOut: () => void;
};

export default function SuccessPage({
    email,
    onSignOut,
}: SuccessPageProps) {
    return (<main className="flex min-h-svh items-center justify-center bg-background px-4"> <section className="w-full max-w-md rounded-2xl border p-8 text-center shadow-sm"> <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-green-100 text-3xl text-green-700">
        ✓ </div>

        ```
        <h1 className="text-2xl font-semibold">
            You have successfully signed in!
        </h1>

        <p className="mt-3 text-sm text-muted-foreground">
            Welcome back. You are signed in with:
        </p>

        <p className="mt-2 break-all font-medium">{email}</p>

        <button
            type="button"
            onClick={onSignOut}
            className="mt-8 w-full rounded-lg bg-primary px-4 py-3 text-primary-foreground"
        >
            Sign out
        </button>
    </section>
    </main>


    );
}
