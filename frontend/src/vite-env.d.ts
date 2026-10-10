/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the auth service, e.g. http://localhost:3001 */
  readonly VITE_AUTH_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
