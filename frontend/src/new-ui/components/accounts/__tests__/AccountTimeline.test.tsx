import { render, screen } from '@testing-library/react';
import AccountTimeline from '../AccountTimeline';
import { UIAccount } from '../../../hooks/useAccounts';
import Decimal from 'decimal.js';

describe('AccountTimeline', () => {
    const mockAccounts: UIAccount[] = [
        {
            id: '1',
            name: 'Chase Checking',
            type: 'checking',
            currency: 'USD',
            balance: new Decimal(1000),
            bankName: 'Chase',
            importsStartDate: Date.now() - 365 * 24 * 60 * 60 * 1000, // 1 year ago
            importsEndDate: Date.now() - 30 * 24 * 60 * 60 * 1000, // 1 month ago
        },
        {
            id: '2',
            name: 'Wells Fargo Savings',
            type: 'savings',
            currency: 'USD',
            balance: new Decimal(5000),
            bankName: 'Wells Fargo',
            importsStartDate: Date.now() - 180 * 24 * 60 * 60 * 1000, // 6 months ago
            importsEndDate: Date.now() - 10 * 24 * 60 * 60 * 1000, // 10 days ago
        },
        {
            id: '3',
            name: 'Credit Card',
            type: 'credit_card',
            currency: 'USD',
            balance: new Decimal(-500),
            bankName: 'Citi',
            // No import dates
        },
    ];

    it('renders timeline with account names', () => {
        render(<AccountTimeline accounts={mockAccounts} />);

        expect(screen.getByText('Account Import Timeline')).toBeInTheDocument();
        expect(screen.getByText('Chase Checking')).toBeInTheDocument();
        expect(screen.getByText('Wells Fargo Savings')).toBeInTheDocument();
        expect(screen.getByText('Credit Card')).toBeInTheDocument();
    });

    it('shows "No data" for accounts without import dates', () => {
        render(<AccountTimeline accounts={mockAccounts} />);

        const creditCardRow = screen.getByText('Credit Card').closest('.timeline-account-row');
        expect(creditCardRow).toBeInTheDocument();
        expect(creditCardRow?.querySelector('.timeline-no-data')).toBeInTheDocument();
    });

    it('renders timeline bars for accounts with import dates', () => {
        render(<AccountTimeline accounts={mockAccounts} />);

        const timelineBars = document.querySelectorAll('.timeline-bar');
        expect(timelineBars.length).toBe(2); // Two accounts have import dates
    });

    it('displays empty state when no accounts provided', () => {
        render(<AccountTimeline accounts={[]} />);

        expect(screen.getByText('No accounts to display')).toBeInTheDocument();
    });

    it('renders date range in header', () => {
        render(<AccountTimeline accounts={mockAccounts} />);

        const timelineHeader = document.querySelector('.timeline-date-range');
        expect(timelineHeader).toBeInTheDocument();
        // Check for two date formats safely - start date and end date (e.g., "Sep 4, 2024Sep 4, 2025")
        const dateText = timelineHeader?.textContent || '';
        expect(dateText).toMatch(/^[A-Za-z]{3} \d{1,2}, \d{4}[A-Za-z]{3} \d{1,2}, \d{4}$/);
    });

    it('includes tooltip information for timeline bars', () => {
        render(<AccountTimeline accounts={mockAccounts} />);

        const timelineBars = document.querySelectorAll('.timeline-bar');
        timelineBars.forEach(bar => {
            expect(bar.getAttribute('title')).toMatch(/: \w+ \d+, \d+ - \w+ \d+, \d+/);
        });
    });
});
