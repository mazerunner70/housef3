// Zod schemas for Account types
// These schemas provide runtime validation for Account-related data

import { z } from 'zod';
import { Decimal } from 'decimal.js';

// Custom Zod transform for Decimal.js
// Only accepts strings (from API) or existing Decimal objects
// Numbers indicate a bug - they should be converted to Decimal earlier in the system
const DecimalSchema = z.union([
    z.string(),
    z.instanceof(Decimal)
]).transform((val) => {
    if (val instanceof Decimal) return val;
    return new Decimal(val);
});

// Account Enums - using z.enum for better TypeScript integration
export const AccountTypeSchema = z.enum([
    "checking",
    "savings",
    "credit_card",
    "investment",
    "loan",
    "other"
]);

export const CurrencySchema = z.enum([
    "USD",
    "EUR",
    "GBP",
    "CAD",
    "JPY",
    "AUD",
    "CHF",
    "CNY",
    "other"
]);

// Core Account Schema
export const AccountSchema = z.object({
    accountId: z.string(),
    userId: z.string(),
    accountName: z.string(),
    accountType: AccountTypeSchema,
    institution: z.string(),
    balance: DecimalSchema,
    currency: CurrencySchema,
    notes: z.string().optional(),
    isActive: z.boolean(),
    defaultFileMapId: z.string().optional(),
    lastTransactionDate: z.number().nullable().optional(), // milliseconds since epoch, can be null
    createdAt: z.number(),
    updatedAt: z.number(),
});

// Account Creation Schema
export const AccountCreateSchema = z.object({
    accountName: z.string().min(1, "Account name is required"),
    accountType: AccountTypeSchema,
    institution: z.string().min(1, "Institution is required"),
    balance: DecimalSchema,
    currency: CurrencySchema,
    notes: z.string().optional(),
    defaultFileMapId: z.string().optional(),
});

// Account Update Schema
export const AccountUpdateSchema = z.object({
    accountName: z.string().min(1).optional(),
    accountType: AccountTypeSchema.optional(),
    institution: z.string().min(1).optional(),
    balance: DecimalSchema.optional(),
    currency: CurrencySchema.optional(),
    notes: z.string().optional(),
    isActive: z.boolean().optional(),
    defaultFileMapId: z.string().optional(),
});

// API Response Schemas
export const UserSchema = z.object({
    id: z.string(),
    email: z.string().email().optional(), // Make email optional
    auth_time: z.string().optional(), // Make auth_time optional
});

export const AccountListResponseSchema = z.object({
    accounts: z.array(AccountSchema),
    user: z.string(), // User is just a string (user ID)
    metadata: z.object({
        totalAccounts: z.number(),
    }).optional(), // Metadata is optional
});

// Account Summary Schema
export const AccountSummarySchema = z.object({
    accountId: z.string(),
    accountName: z.string(),
    accountType: AccountTypeSchema,
    institution: z.string(),
    balance: DecimalSchema,
    currency: CurrencySchema,
    isActive: z.boolean(),
});

// Account Stats Schema
export const CurrencyBreakdownSchema = z.object({
    currency: CurrencySchema,
    totalBalance: DecimalSchema,
    accountCount: z.number(),
});

export const TypeBreakdownSchema = z.object({
    accountType: AccountTypeSchema,
    totalBalance: DecimalSchema,
    accountCount: z.number(),
});

export const RecentActivitySchema = z.object({
    accountId: z.string(),
    lastTransactionDate: z.number(),
    transactionCount: z.number(),
});

export const AccountStatsSchema = z.object({
    totalBalance: DecimalSchema,
    accountCount: z.number(),
    activeAccountCount: z.number(),
    currencyBreakdown: z.array(CurrencyBreakdownSchema),
    typeBreakdown: z.array(TypeBreakdownSchema),
    recentActivity: z.array(RecentActivitySchema),
});

// Error Schemas
export const AccountErrorSchema = z.object({
    code: z.string(),
    message: z.string(),
    field: z.string().optional(),
    details: z.any().optional(),
});

export const AccountApiResponseSchema = z.object({
    success: z.boolean(),
    data: z.any().optional(),
    error: AccountErrorSchema.optional(),
    message: z.string().optional(),
});

// Account Filters Schema
export const AccountFiltersSchema = z.object({
    accountTypes: z.array(AccountTypeSchema).optional(),
    currencies: z.array(CurrencySchema).optional(),
    institutions: z.array(z.string()).optional(),
    isActive: z.boolean().optional(),
    hasTransactions: z.boolean().optional(),
    balanceRange: z.object({
        min: DecimalSchema,
        max: DecimalSchema,
    }).optional(),
});

// Type inference from schemas (these match your existing TypeScript types)
export type Account = z.infer<typeof AccountSchema>;
export type AccountCreate = z.infer<typeof AccountCreateSchema>;
export type AccountUpdate = z.infer<typeof AccountUpdateSchema>;
export type AccountListResponse = z.infer<typeof AccountListResponseSchema>;
export type AccountSummary = z.infer<typeof AccountSummarySchema>;
export type AccountStats = z.infer<typeof AccountStatsSchema>;
export type AccountError = z.infer<typeof AccountErrorSchema>;
export type AccountApiResponse<T = any> = z.infer<typeof AccountApiResponseSchema> & { data?: T };
export type AccountFilters = z.infer<typeof AccountFiltersSchema>;

// Export the enum values for backward compatibility
export const AccountType = {
    CHECKING: "checking" as const,
    SAVINGS: "savings" as const,
    CREDIT_CARD: "credit_card" as const,
    INVESTMENT: "investment" as const,
    LOAN: "loan" as const,
    OTHER: "other" as const,
} as const;

export const Currency = {
    USD: "USD" as const,
    EUR: "EUR" as const,
    GBP: "GBP" as const,
    CAD: "CAD" as const,
    JPY: "JPY" as const,
    AUD: "AUD" as const,
    CHF: "CHF" as const,
    CNY: "CNY" as const,
    OTHER: "other" as const,
} as const;
