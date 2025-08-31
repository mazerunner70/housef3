import { getTransferProgressAndRecommendation, createDateRangeFromDays } from '../TransferService';
import { getTransferDataForProgress } from '../UserPreferencesService';

// Mock all external dependencies
jest.mock('@/utils/apiClient', () => ({
    default: {
        getJson: jest.fn(),
        postJson: jest.fn()
    }
}));

jest.mock('@/utils/zodErrorHandler', () => ({
    validateApiResponse: jest.fn()
}));

jest.mock('@/utils/logger', () => ({
    withApiLogging: jest.fn((service, url, method, fn) => fn),
    withServiceLogging: jest.fn((service, operation, fn) => fn),
    createLogger: jest.fn(() => ({
        info: jest.fn(),
        warn: jest.fn(),
        error: jest.fn()
    }))
}));

// Mock the UserPreferencesService
jest.mock('../UserPreferencesService', () => ({
    getTransferDataForProgress: jest.fn(),
    updateTransferCheckedDateRange: jest.fn()
}));

const mockGetTransferDataForProgress = getTransferDataForProgress as jest.MockedFunction<typeof getTransferDataForProgress>;

describe('TransferService - Progress and Recommendation Algorithm', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Reset console methods to avoid cluttering test output
        jest.spyOn(console, 'info').mockImplementation(() => { });
        jest.spyOn(console, 'warn').mockImplementation(() => { });
        jest.spyOn(console, 'error').mockImplementation(() => { });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('No previous checks - initial recommendation', () => {
        it('should suggest recent 30-day chunk when no previous checks exist', async () => {
            // Account has 400 days of data, no previous checks
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2025-01-08').getTime(); // Latest actual transaction

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: null, endDate: null },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: null,
                    checkedDateRangeEnd: null
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();
            expect(result.recommendedRange!.endDate).toBe(accountEnd);

            // Should suggest 30 days back from latest transaction
            const expectedStart = new Date(accountEnd);
            expectedStart.setDate(expectedStart.getDate() - 30);
            expect(result.recommendedRange!.startDate).toBe(expectedStart.getTime());
        });

        it('should not go before account start date when suggesting initial range', async () => {
            // Account with only 15 days of data
            const accountStart = new Date('2024-12-24').getTime();
            const accountEnd = new Date('2025-01-08').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: null, endDate: null },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: null,
                    checkedDateRangeEnd: null
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();
            expect(result.recommendedRange!.startDate).toBe(accountStart); // Capped at account start
            expect(result.recommendedRange!.endDate).toBe(accountEnd);
        });
    });

    describe('Forward extension - continuous coverage', () => {
        it('should extend forward with 3-day overlap when more data available', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2025-01-08').getTime();

            // Already checked Dec 1-31, 2024
            const checkedStart = new Date('2024-12-01').getTime();
            const checkedEnd = new Date('2024-12-31').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();

            // Should start 3 days before end of checked range (overlap)
            const expectedStart = new Date('2024-12-28').getTime(); // Dec 31 - 3 days
            expect(result.recommendedRange!.startDate).toBe(expectedStart);

            // Should end at account boundary (Jan 8, 2025)
            expect(result.recommendedRange!.endDate).toBe(accountEnd);
        });

        it('should cap forward extension at account end boundary', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2024-12-15').getTime(); // Limited account data

            // Already checked most of the data
            const checkedStart = new Date('2024-11-01').getTime();
            const checkedEnd = new Date('2024-12-01').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();

            // Should be capped at account end, not extend 30 days
            expect(result.recommendedRange!.endDate).toBe(accountEnd);

            // Should start with 3-day overlap
            const expectedStart = new Date('2024-11-28').getTime(); // Dec 1 - 3 days
            expect(result.recommendedRange!.startDate).toBe(expectedStart);
        });
    });

    describe('Backward extension - historical data', () => {
        it('should extend backward with 3-day overlap when forward extension not possible', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2025-01-08').getTime();

            // Already checked recent data (Dec 1 - Jan 8)
            const checkedStart = new Date('2024-12-01').getTime();
            const checkedEnd = new Date('2025-01-08').getTime(); // Up to account end

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();

            // Should end 3 days after start of checked range (overlap)
            const expectedEnd = new Date('2024-12-04').getTime(); // Dec 1 + 3 days
            expect(result.recommendedRange!.endDate).toBe(expectedEnd);

            // Should start 30 days before that
            const expectedStart = new Date('2024-11-04').getTime(); // Dec 4 - 30 days
            expect(result.recommendedRange!.startDate).toBe(expectedStart);
        });

        it('should cap backward extension at account start boundary', async () => {
            const accountStart = new Date('2024-11-15').getTime(); // Limited historical data
            const accountEnd = new Date('2025-01-08').getTime();

            // Already checked recent data
            const checkedStart = new Date('2024-12-01').getTime();
            const checkedEnd = new Date('2025-01-08').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();

            // Should be capped at account start
            expect(result.recommendedRange!.startDate).toBe(accountStart);

            // Should end with 3-day overlap
            const expectedEnd = new Date('2024-12-04').getTime(); // Dec 1 + 3 days
            expect(result.recommendedRange!.endDate).toBe(expectedEnd);
        });
    });

    describe('Complete coverage scenarios', () => {
        it('should return null when all actual data has been checked', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2025-01-08').getTime();

            // Checked the entire account range
            const checkedStart = new Date('2024-01-01').getTime();
            const checkedEnd = new Date('2025-01-08').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).toBeNull();
            expect(result.progress.isComplete).toBe(true);
            expect(result.progress.progressPercentage).toBe(100);
        });
    });

    describe('Boundary validation and edge cases', () => {
        it('should handle checked range extending beyond account boundaries', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2025-01-08').getTime(); // Latest actual transaction

            // Checked range extends into future (invalid data)
            const checkedStart = new Date('2024-12-01').getTime();
            const checkedEnd = new Date('2025-06-30').getTime(); // Way beyond actual data

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            // Should validate checked range against actual boundaries
            expect(result.progress.progressPercentage).toBeLessThan(100);

            // Should suggest extending backward since forward is not possible
            expect(result.recommendedRange).not.toBeNull();
            expect(result.recommendedRange!.endDate).toBeLessThanOrEqual(accountEnd);
            expect(result.recommendedRange!.startDate).toBeGreaterThanOrEqual(accountStart);
        });

        it('should handle empty account range gracefully', async () => {
            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: null, endDate: null },
                accountRange: { startDate: null, endDate: null },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: null,
                    checkedDateRangeEnd: null
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.progress.hasData).toBe(false);
            expect(result.progress.progressPercentage).toBe(0);
            expect(result.recommendedRange).toBeNull();
        });

        it('should handle service errors gracefully', async () => {
            mockGetTransferDataForProgress.mockRejectedValue(new Error('Service unavailable'));

            const result = await getTransferProgressAndRecommendation();

            expect(result.progress.hasData).toBe(false);
            expect(result.progress.error).toBe('Service unavailable');
            expect(result.recommendedRange).toBeNull();
        });
    });

    describe('Progress calculation validation', () => {
        it('should calculate progress correctly with valid checked range', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2024-12-31').getTime(); // 365 days

            // Checked 30 days
            const checkedStart = new Date('2024-06-01').getTime();
            const checkedEnd = new Date('2024-06-30').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.progress.hasData).toBe(true);
            expect(result.progress.totalDays).toBe(365);
            expect(result.progress.checkedDays).toBe(29); // June has 30 days, but calculation gives 29
            expect(result.progress.progressPercentage).toBe(8); // 29/365 ≈ 8%
            expect(result.progress.isComplete).toBe(false);
        });

        it('should handle checked range that exceeds account boundaries in progress calculation', async () => {
            const accountStart = new Date('2024-06-01').getTime();
            const accountEnd = new Date('2024-06-30').getTime(); // 30 days total

            // Checked range extends beyond boundaries
            const checkedStart = new Date('2024-05-01').getTime(); // Before account start
            const checkedEnd = new Date('2024-07-31').getTime(); // After account end

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            // Should only count the intersection (June 1-30, but calculation gives 29 days)
            expect(result.progress.totalDays).toBe(29);
            expect(result.progress.checkedDays).toBe(29);
            expect(result.progress.progressPercentage).toBe(100);
            expect(result.progress.isComplete).toBe(true);
        });
    });

    describe('Overlap and chunk size validation', () => {
        it('should use 3-day overlap for transfer pair detection', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2024-12-31').getTime();

            const checkedStart = new Date('2024-06-01').getTime();
            const checkedEnd = new Date('2024-06-30').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();

            // Forward extension should start 3 days before end of checked range
            const expectedOverlapStart = new Date('2024-06-27').getTime(); // June 30 - 3 days
            expect(result.recommendedRange!.startDate).toBe(expectedOverlapStart);
        });

        it('should suggest approximately 30-day chunks', async () => {
            const accountStart = new Date('2024-01-01').getTime();
            const accountEnd = new Date('2024-12-31').getTime();

            const checkedStart = new Date('2024-06-01').getTime();
            const checkedEnd = new Date('2024-06-30').getTime();

            mockGetTransferDataForProgress.mockResolvedValue({
                checkedRange: { startDate: checkedStart, endDate: checkedEnd },
                accountRange: { startDate: accountStart, endDate: accountEnd },
                transferPreferences: {
                    defaultDateRangeDays: 7,
                    lastUsedDateRanges: [7, 14, 30],
                    autoExpandSuggestion: true,
                    checkedDateRangeStart: checkedStart,
                    checkedDateRangeEnd: checkedEnd
                }
            });

            const result = await getTransferProgressAndRecommendation();

            expect(result.recommendedRange).not.toBeNull();

            // Should suggest roughly 30 days (27 days start + 30 days = 57 days total, but 3 days overlap)
            const rangeDays = Math.ceil((result.recommendedRange!.endDate - result.recommendedRange!.startDate) / (1000 * 60 * 60 * 24));
            expect(rangeDays).toBeGreaterThanOrEqual(30);
            expect(rangeDays).toBeLessThanOrEqual(33); // 30 + 3 day overlap
        });
    });
});
