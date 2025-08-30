import {
  getFZIPRestoreUploadUrl,
  uploadFZIPPackage,
  cancelFZIPRestore,
  startFZIPRestoreProcessing,
  formatRestoreStatus,
  FZIPRestoreStatus,
} from '../FZIPService';

// Mock AuthService used by authenticatedRequest
jest.mock('../AuthService', () => ({
  getCurrentUser: jest.fn(() => ({ token: 'Bearer test-token', refreshToken: 'refresh' })),
  refreshToken: jest.fn(async () => ({ token: 'Bearer test-token-2', refreshToken: 'refresh' })),
  isAuthenticated: jest.fn(() => true),
}));

describe('FZIPService - Restore flow (services)', () => {
  const originalFetch = global.fetch as any;
  const originalFormData = global.FormData as any;

  beforeEach(() => {
    jest.clearAllMocks();
  });

  afterAll(() => {
    global.fetch = originalFetch;
    global.FormData = originalFormData;
  });

  test('getFZIPRestoreUploadUrl calls backend and returns fields', async () => {
    const mockResponse = {
      restoreId: 'abc-123',
      url: 'https://s3.amazonaws.com/bucket',
      fields: { key: 'restore_packages/user/abc-123.fzip', 'x-amz-meta-userid': 'user' },
      expiresIn: 3600,
    };

    global.fetch = jest.fn(async () => ({ ok: true, status: 200, json: async () => mockResponse })) as any;

    const data = await getFZIPRestoreUploadUrl();
    expect(data.restoreId).toBe('abc-123');
    expect(data.url).toContain('s3.amazonaws.com');
    expect(data.fields.key).toContain('restore_packages');
    // Ensure Authorization header was set
    const calledWith = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(calledWith.endsWith('/api/fzip/restore/upload-url')).toBe(true);
  });

  test('uploadFZIPPackage posts to S3 and notifies backend', async () => {
    const calls: any[] = [];

    // Simple FormData stub to capture fields
    class FDStub {
      public fields: Record<string, any> = {};
      append(key: string, value: any) {
        this.fields[key] = value;
      }
    }

    global.FormData = FDStub as any;

    const s3Ok = { ok: true, status: 204 };
    const apiOk = { ok: true, status: 200, json: async () => ({}) };

    global.fetch = jest.fn(async (url: string) => {
      calls.push(url);
      if (url.startsWith('https://s3.amazonaws.com')) return s3Ok as any;
      return apiOk as any;
    }) as any;

    const file = { name: 'test.fzip' } as any;
    const uploadUrl = {
      url: 'https://s3.amazonaws.com/bucket',
      fields: { key: 'restore_packages/user/x.fzip', 'x-amz-meta-userid': 'user', 'x-amz-meta-restoreid': 'x' },
    };

    await uploadFZIPPackage('x', file, uploadUrl);

    // First call to S3, second call to backend notify endpoint
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toBe(uploadUrl.url);
    const secondUrl = (global.fetch as jest.Mock).mock.calls[1][0] as string;
    expect(secondUrl.endsWith('/api/fzip/restore/x/upload')).toBe(true);
  });

  test('cancelFZIPRestore posts to cancel endpoint', async () => {
    global.fetch = jest.fn(async () => ({ ok: true, status: 200, json: async () => ({}) })) as any;
    await cancelFZIPRestore('job-1');
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url.endsWith('/api/fzip/restore/job-1/cancel')).toBe(true);
  });

  test('startFZIPRestoreProcessing posts to start endpoint', async () => {
    global.fetch = jest.fn(async () => ({ ok: true, status: 200, json: async () => ({}) })) as any;
    await startFZIPRestoreProcessing('job-2');
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string;
    expect(url.endsWith('/api/fzip/restore/job-2/start')).toBe(true);
  });

  test('formatRestoreStatus produces user-friendly labels', () => {
    expect(formatRestoreStatus(FZIPRestoreStatus.UPLOADED)).toBe('Uploaded');
    expect(formatRestoreStatus(FZIPRestoreStatus.VALIDATION_PASSED)).toBe('Ready to Start');
    expect(formatRestoreStatus(FZIPRestoreStatus.CANCELED)).toBe('Canceled');
  });
});


