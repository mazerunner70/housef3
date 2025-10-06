import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import FZIPRestoreList from '../../components/FZIPRestoreList';

// Mock AuthService to avoid import.meta in its implementation during tests
jest.mock('../../../services/AuthService', () => ({
  getCurrentUser: jest.fn(() => ({ token: 'Bearer test', refreshToken: 'r' })),
  refreshToken: jest.fn(async () => ({ token: 'Bearer test2', refreshToken: 'r' })),
  isAuthenticated: jest.fn(() => true),
}));

jest.mock('../../../services/FZIPService', () => {
  const actual = jest.requireActual('../../../services/FZIPService');
  return {
    ...actual,
    listFZIPRestoreJobs: jest.fn(async () => ({
      restoreJobs: [
        {
          jobId: 'j1',
          status: 'restore_validation_passed',
          createdAt: Date.now(),
          progress: 40,
          currentPhase: 'validated_waiting_to_start',
        },
      ],
    })),
    startFZIPRestoreProcessing: jest.fn(async () => {}),
    cancelFZIPRestore: jest.fn(async () => {}),
    formatRestoreStatus: (s: string) => {
      if (s === 'restore_validation_passed') return 'Validation Passed';
      return s;
    }
  };
});

describe('FZIPRestoreList component', () => {
  test('renders list and shows Start action for validation passed jobs', async () => {
    const jobs = [
      {
        jobId: 'j1',
        status: 'restore_validation_passed',
        createdAt: Date.now(),
        progress: 40,
        currentPhase: 'validated_waiting_to_start',
      },
    ];

    const onDelete = jest.fn(async () => {});
    const onRefreshStatus = jest.fn(async () => jobs[0] as any);
    const onStartRestore = jest.fn(async () => {});

    render(
      <FZIPRestoreList
        restoreJobs={jobs as any}
        onDelete={onDelete}
        onRefreshStatus={onRefreshStatus}
        onStartRestore={onStartRestore}
      />
    );

    // Badge sets title to the formatted status; assert via title to avoid duplicates
    await waitFor(() => expect(screen.getByTitle('Validation Passed')).toBeInTheDocument());
    expect(screen.getByText(/start restore/i)).toBeInTheDocument();
  });
});


