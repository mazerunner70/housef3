import { ENV, apiEndpoint } from '../../utils/env';

describe('env util', () => {
  test('reads API endpoint from import.meta.env polyfill', () => {
    expect(ENV.VITE_API_ENDPOINT).toBe('https://example.com');
    expect(apiEndpoint).toBe('https://example.com/api');
  });
});


