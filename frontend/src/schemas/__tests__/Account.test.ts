// Test file for Account Zod schemas
import { Decimal } from 'decimal.js';
import {
    AccountSchema,
    AccountListResponseSchema,
    AccountCreateSchema,
    AccountUpdateSchema,
    AccountType,
    Currency
} from '../Account';

describe('Account Zod Schemas', () => {
    describe('AccountSchema', () => {
        it('should validate a valid account object', () => {
            const validAccount = {
                accountId: 'acc-123',
                userId: 'user-456',
                accountName: 'My Checking Account',
                accountType: 'checking',
                institution: 'Bank of Example',
                balance: new Decimal('1000.50'),
                currency: 'USD',
                notes: 'Primary checking account',
                isActive: true,
                defaultFileMapId: 'map-789',
                lastTransactionDate: 1640995200000,
                createdAt: 1640995200000,
                updatedAt: 1640995200000,
            };

            const result = AccountSchema.safeParse(validAccount);
            expect(result.success).toBe(true);

            if (result.success) {
                expect(result.data.balance).toBeInstanceOf(Decimal);
                expect(result.data.balance.toString()).toBe('1000.5');
            }
        });

        it('should handle string balance and convert to Decimal', () => {
            const accountWithStringBalance = {
                accountId: 'acc-123',
                userId: 'user-456',
                accountName: 'My Checking Account',
                accountType: 'checking',
                institution: 'Bank of Example',
                balance: '1000.50', // String instead of Decimal
                currency: 'USD',
                isActive: true,
                createdAt: 1640995200000,
                updatedAt: 1640995200000,
            };

            const result = AccountSchema.safeParse(accountWithStringBalance);
            expect(result.success).toBe(true);

            if (result.success) {
                expect(result.data.balance).toBeInstanceOf(Decimal);
                expect(result.data.balance.toString()).toBe('1000.5');
            }
        });

        it('should reject number balance as it indicates a bug', () => {
            const accountWithNumberBalance = {
                accountId: 'acc-123',
                userId: 'user-456',
                accountName: 'My Checking Account',
                accountType: 'checking',
                institution: 'Bank of Example',
                balance: 1000.50, // Number should be rejected - indicates bug
                currency: 'USD',
                isActive: true,
                createdAt: 1640995200000,
                updatedAt: 1640995200000,
            };

            const result = AccountSchema.safeParse(accountWithNumberBalance);
            expect(result.success).toBe(false);

            if (!result.success) {
                // Should have validation error for balance field
                expect(result.error.issues.some(issue =>
                    issue.path.includes('balance')
                )).toBe(true);
            }
        });

        it('should reject invalid account type', () => {
            const invalidAccount = {
                accountId: 'acc-123',
                userId: 'user-456',
                accountName: 'My Checking Account',
                accountType: 'invalid_type', // Invalid account type
                institution: 'Bank of Example',
                balance: new Decimal('1000.50'),
                currency: 'USD',
                isActive: true,
                createdAt: 1640995200000,
                updatedAt: 1640995200000,
            };

            const result = AccountSchema.safeParse(invalidAccount);
            expect(result.success).toBe(false);
        });

        it('should reject missing required fields', () => {
            const incompleteAccount = {
                accountId: 'acc-123',
                // Missing userId, accountName, etc.
                accountType: 'checking',
                institution: 'Bank of Example',
                balance: new Decimal('1000.50'),
                currency: 'USD',
                isActive: true,
            };

            const result = AccountSchema.safeParse(incompleteAccount);
            expect(result.success).toBe(false);
        });
    });

    describe('AccountListResponseSchema', () => {
        it('should validate a valid account list response', () => {
            const validResponse = {
                accounts: [
                    {
                        accountId: 'acc-123',
                        userId: 'user-456',
                        accountName: 'My Checking Account',
                        accountType: 'checking',
                        institution: 'Bank of Example',
                        balance: '1000.50',
                        currency: 'USD',
                        isActive: true,
                        createdAt: 1640995200000,
                        updatedAt: 1640995200000,
                    }
                ],
                user: {
                    id: 'user-456',
                    email: 'user@example.com',
                    auth_time: '2024-01-01T00:00:00Z',
                }
            };

            const result = AccountListResponseSchema.safeParse(validResponse);
            expect(result.success).toBe(true);

            if (result.success) {
                expect(result.data.accounts).toHaveLength(1);
                expect(result.data.accounts[0].balance).toBeInstanceOf(Decimal);
            }
        });
    });

    describe('AccountCreateSchema', () => {
        it('should validate account creation data', () => {
            const createData = {
                accountName: 'New Account',
                accountType: 'savings',
                institution: 'Credit Union',
                balance: '500.00',
                currency: 'USD',
                notes: 'Savings account',
            };

            const result = AccountCreateSchema.safeParse(createData);
            expect(result.success).toBe(true);
        });

        it('should reject empty account name', () => {
            const createData = {
                accountName: '', // Empty name should fail
                accountType: 'savings',
                institution: 'Credit Union',
                balance: '500.00',
                currency: 'USD',
            };

            const result = AccountCreateSchema.safeParse(createData);
            expect(result.success).toBe(false);
        });
    });

    describe('AccountUpdateSchema', () => {
        it('should validate partial account update data', () => {
            const updateData = {
                accountName: 'Updated Account Name',
                balance: '750.00',
            };

            const result = AccountUpdateSchema.safeParse(updateData);
            expect(result.success).toBe(true);

            if (result.success) {
                expect(result.data.balance).toBeInstanceOf(Decimal);
            }
        });

        it('should allow empty update object', () => {
            const updateData = {};

            const result = AccountUpdateSchema.safeParse(updateData);
            expect(result.success).toBe(true);
        });
    });

    describe('Enum constants', () => {
        it('should provide backward compatible enum values', () => {
            expect(AccountType.CHECKING).toBe('checking');
            expect(AccountType.SAVINGS).toBe('savings');
            expect(AccountType.CREDIT_CARD).toBe('credit_card');

            expect(Currency.USD).toBe('USD');
            expect(Currency.EUR).toBe('EUR');
            expect(Currency.GBP).toBe('GBP');
        });
    });
});
