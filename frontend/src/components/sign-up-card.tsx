import { useActionState } from 'react';
import { LoaderCircle } from 'lucide-react';

import { Button } from '../shadcn/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '../shadcn/components/ui/card';
import { Input } from '../shadcn/components/ui/input';
import { Label } from '../shadcn/components/ui/label';

import styles from './sign-in-card.module.scss';

export interface SignUpCredentials {
  name: string;
  email: string;
  password: string;
}

export interface SignUpCardProps {
  onSignUp: (credentials: SignUpCredentials) => Promise<void>;
  onSignIn?: () => void;
  signInHref?: string;
  termsHref?: string;
  privacyHref?: string;
  id?: string;
}

export function SignUpCard({
  onSignUp,
  onSignIn,
  signInHref = '/sign-in',
  termsHref = '/terms',
  privacyHref = '/privacy',
  id = 'sign-up',
}: SignUpCardProps) {
  const [error, signUpAction, pending] = useActionState(
    async (_prev: string | null, data: FormData): Promise<string | null> => {
      try {
        await onSignUp({
          name: String(data.get('name') ?? '').trim(),
          email: String(data.get('email') ?? '').trim(),
          password: String(data.get('password') ?? ''),
        });

        return null;
      } catch (err) {
        return err instanceof Error
          ? err.message
          : 'Sign up failed. Try again.';
      }
    },
    null,
  );

  return (
    <Card id={id} className={styles.card}>
      <CardHeader>
        <CardTitle className={styles.title}>Create your account</CardTitle>
        <CardDescription>
          Enter your details to get started.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form action={signUpAction} className={styles.form}>
          <div className={styles.field}>
            <Label htmlFor={`${id}-name`}>Name</Label>
            <Input
              id={`${id}-name`}
              name="name"
              type="text"
              autoComplete="name"
              placeholder="Your name"
              required
              disabled={pending}
            />
          </div>

          <div className={styles.field}>
            <Label htmlFor={`${id}-email`}>Email</Label>
            <Input
              id={`${id}-email`}
              name="email"
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              required
              disabled={pending}
            />
          </div>

          <div className={styles.field}>
            <Label htmlFor={`${id}-password`}>Password</Label>
            <Input
              id={`${id}-password`}
              name="password"
              type="password"
              autoComplete="new-password"
              minLength={8}
              required
              disabled={pending}
            />
          </div>

          {error && (
            <p role="alert" className={styles.error}>
              {error}
            </p>
          )}

          <Button
            type="submit"
            className={styles.submit}
            disabled={pending}
          >
            {pending && (
              <LoaderCircle className={styles.spinner} aria-hidden />
            )}
            Create account
          </Button>
        </form>
      </CardContent>

      <CardFooter className={styles.footer}>
        <p>
          Already have an account?{' '}
          {onSignIn ? (
            <button
              type="button"
              onClick={onSignIn}
              className={styles.strongLink}
            >
              Sign in
            </button>
          ) : (
            <a href={signInHref} className={styles.strongLink}>
              Sign in
            </a>
          )}
        </p>

        <p>
          By continuing you agree to the{' '}
          <button
            type="button"
            className={styles.link}
            onClick={() => console.log('Terms clicked:', termsHref)}
          >
            Terms
          </button>{' '}
          and{' '}
          <button
            type="button"
            className={styles.link}
            onClick={() => console.log('Privacy policy clicked:', privacyHref)}
          >
            Privacy policy
          </button>
          .
        </p>
      </CardFooter>
    </Card>
  );
}
