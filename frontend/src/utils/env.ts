type Env = {
  VITE_API_ENDPOINT: string;
};

function readEnv(): Env {
  // In tests, jest.setup.ts sets global.import.meta.env
  const polyfilled = (globalThis as any)?.import?.meta?.env;
  // In app/runtime, rely on Vite's build-time replacement
  // Suppress TS in Jest (which may compile with non-ES module) while still letting Vite inline at build time
  // @ts-expect-error: import.meta is only valid in ESM; Vite will replace this in production builds
  const viteEnv = polyfilled ?? import.meta.env;

  const endpoint = viteEnv?.VITE_API_ENDPOINT ?? 'http://localhost:5173';
  return { VITE_API_ENDPOINT: endpoint };
}

export const ENV = readEnv();
export const apiEndpoint = `${ENV.VITE_API_ENDPOINT}/api`;


