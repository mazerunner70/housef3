import '@testing-library/jest-dom';

// Polyfill import.meta.env for tests
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(global as any).import = { meta: { env: { VITE_API_ENDPOINT: 'https://example.com', MODE: 'test' } } } as any;


