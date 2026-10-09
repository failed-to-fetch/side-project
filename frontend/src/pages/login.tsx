import {GitCommitHorizontal, Package, Users, type LucideIcon} from 'lucide-react';

import {SignInCard, type SignInCredentials} from '../components/sign-in-card';
import {Badge} from '../shadcn/components/ui/badge';

import styles from './login.module.scss';

export interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
}

export interface LoginPageProps {
  onSignIn: (credentials: SignInCredentials) => Promise<void>;
  productName?: string;
  description?: string;
  features?: readonly Feature[];
}

const defaultFeatures: readonly Feature[] = [
  {icon: GitCommitHorizontal, title: 'History snapshots', description: 'Daily, weekly or per release.'},
  {icon: Package, title: 'Dependency changes', description: 'When each package came and went.'},
  {icon: Users, title: 'Owners', description: 'Who knows which part of the code.'},
];

export default function LoginPage({
  onSignIn,
  productName = '[Product]',
  description = 'Point it at a repository. Get snapshots of files, dependencies and ownership across its whole history.',
  features = defaultFeatures,
}: LoginPageProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <span className={styles.brand}>{productName}</span>
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.hero}>
          <Badge variant="outline" className={styles.badge}>
            Git history analysis
          </Badge>

          <h1 className={styles.headline}>See how a codebase grew, commit by commit.</h1>

          <p className={styles.description}>{description}</p>

          <ul className={styles.features}>
            {features.map(({icon: Icon, title, description}) => (
              <li key={title} className={styles.feature}>
                <Icon className={styles.featureIcon} aria-hidden />
                <p className={styles.featureTitle}>{title}</p>
                <p className={styles.featureDescription}>{description}</p>
              </li>
            ))}
          </ul>
        </section>

        <SignInCard onSignIn={onSignIn} />
      </main>
    </div>
  );
}
