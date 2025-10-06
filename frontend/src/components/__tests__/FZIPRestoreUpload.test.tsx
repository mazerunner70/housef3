import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FZIPRestoreUpload from '../../components/FZIPRestoreUpload';

// Mock service calls used by the component
jest.mock('../../../services/FZIPService', () => ({
  getFZIPRestoreUploadUrl: jest.fn(async () => ({
    restoreId: 'rid',
    url: 'https://s3.amazonaws.com/bucket',
    fields: { key: 'restore_packages/u/rid.fzip', 'x-amz-meta-userid': 'u', 'x-amz-meta-restoreid': 'rid' },
    expiresIn: 3600,
  })),
}));

describe('FZIPRestoreUpload component', () => {
  test('renders and triggers upload URL request on file select', async () => {
    const onUploaded = jest.fn();
    const { container } = render(<FZIPRestoreUpload onUploaded={onUploaded} />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File([new ArrayBuffer(10)], 'test.fzip', { type: 'application/zip' });
    await waitFor(() => expect(input).toBeInTheDocument());

    fireEvent.change(input, { target: { files: [file] } });

    // Mock fetch for S3 and backend notify
    const s3Ok = { ok: true, status: 204 } as any;
    const apiOk = { ok: true, status: 200, json: async () => ({}) } as any;
    // Ensure fetch exists for spying (jsdom may not define it)
    if (!('fetch' in globalThis)) {
      (globalThis as any).fetch = (async () => ({ ok: true })) as any;
    }
    const fetchMock = jest
      .spyOn(globalThis as any, 'fetch')
      .mockImplementation(async (url: string) => {
      if (url.startsWith('https://s3.amazonaws.com')) return s3Ok;
      return apiOk;
    });

    // Click Start Restore to trigger upload
    fireEvent.click(screen.getByText(/start restore/i));

    await waitFor(() => expect(onUploaded).toHaveBeenCalled());
    fetchMock.mockRestore();
  });
});


