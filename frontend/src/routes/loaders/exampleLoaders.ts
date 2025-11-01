import { LoaderFunctionArgs, redirect } from 'react-router-dom';
import { QueryClient } from '@tanstack/react-query';

/**
 * Example Route Loaders
 * 
 * This file contains example loaders that demonstrate various patterns.
 * Use these as templates for creating your own loaders.
 */

// ============================================================================
// EXAMPLE 1: Simple Data Loader
// ============================================================================

export interface Account {
    id: string;
    name: string;
    balance: number;
}

export const simpleAccountLoader = async ({ params }: LoaderFunctionArgs) => {
    const { accountId } = params;

    // Fetch account data
    const response = await fetch(`/api/accounts/${accountId}`);

    if (!response.ok) {
        throw new Response('Account not found', { status: 404 });
    }

    const account = await response.json();
    return { account };
};

// Usage in component:
// const { account } = useLoaderData() as { account: Account };

// ============================================================================
// EXAMPLE 2: Loader with URL Search Params
// ============================================================================

export interface Transaction {
    id: string;
    amount: number;
    date: string;
}

export const transactionsWithFiltersLoader = async ({ request }: LoaderFunctionArgs) => {
    // Parse URL search params
    const url = new URL(request.url);
    const startDate = url.searchParams.get('startDate') || undefined;
    const endDate = url.searchParams.get('endDate') || undefined;
    const category = url.searchParams.get('category') || undefined;

    // Build query string
    const queryParams = new URLSearchParams();
    if (startDate) queryParams.set('startDate', startDate);
    if (endDate) queryParams.set('endDate', endDate);
    if (category) queryParams.set('category', category);

    // Fetch with filters
    const response = await fetch(`/api/transactions?${queryParams}`);
    const transactions = await response.json();

    return {
        transactions,
        filters: { startDate, endDate, category }
    };
};

// Usage:
// Navigate to: /transactions?startDate=2024-01-01&category=food
// const { transactions, filters } = useLoaderData();

// ============================================================================
// EXAMPLE 3: Loader with Authentication Check
// ============================================================================

export const protectedDataLoader = async ({ params }: LoaderFunctionArgs) => {
    // Check if user is authenticated
    const token = localStorage.getItem('authToken');
    if (!token) {
        // Redirect to login
        return redirect('/login');
    }

    // Fetch protected data
    const response = await fetch(`/api/protected/${params.id}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });

    if (response.status === 401) {
        // Token expired, redirect to login
        return redirect('/login');
    }

    const data = await response.json();
    return { data };
};

// ============================================================================
// EXAMPLE 4: Loader with React Query Integration
// ============================================================================

export const createQueryLoader = (queryClient: QueryClient) => {
    return async ({ params }: LoaderFunctionArgs) => {
        const { accountId } = params;

        // Use React Query's ensureQueryData to fetch and cache
        const account = await queryClient.ensureQueryData({
            queryKey: ['account', accountId],
            queryFn: async () => {
                const response = await fetch(`/api/accounts/${accountId}`);
                if (!response.ok) throw new Error('Failed to fetch account');
                return response.json();
            },
            staleTime: 1000 * 60 * 5, // 5 minutes
        });

        return { account };
    };
};

// Usage in router.tsx:
// {
//   path: 'accounts/:accountId',
//   loader: createQueryLoader(queryClient)
// }

// ============================================================================
// EXAMPLE 5: Loader with Multiple Data Sources
// ============================================================================

export const dashboardLoader = async () => {
    // Fetch multiple data sources in parallel
    const [accounts, transactions, categories] = await Promise.all([
        fetch('/api/accounts').then(r => r.json()),
        fetch('/api/transactions/recent').then(r => r.json()),
        fetch('/api/categories').then(r => r.json())
    ]);

    return {
        accounts,
        transactions,
        categories
    };
};

// ============================================================================
// EXAMPLE 6: Conditional Loading Based on Permissions
// ============================================================================

export const roleBasedLoader = async ({ params }: LoaderFunctionArgs) => {
    const { userId } = params;

    // Get current user role
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const isAdmin = currentUser.role === 'admin';

    // Fetch different data based on role
    if (isAdmin) {
        // Admin can see all data
        const response = await fetch(`/api/admin/users/${userId}`);
        return { user: await response.json(), isAdmin: true };
    } else {
        // Regular users can only see their own data
        if (currentUser.id !== userId) {
            throw new Response('Forbidden', { status: 403 });
        }
        const response = await fetch(`/api/users/${userId}`);
        return { user: await response.json(), isAdmin: false };
    }
};

// ============================================================================
// EXAMPLE 7: Loader with Error Handling
// ============================================================================

export const robustLoader = async ({ params }: LoaderFunctionArgs) => {
    const { resourceId } = params;

    try {
        const response = await fetch(`/api/resources/${resourceId}`);

        if (response.status === 404) {
            throw new Response('Resource not found', {
                status: 404,
                statusText: 'Not Found'
            });
        }

        if (response.status === 403) {
            throw new Response('You do not have permission to view this resource', {
                status: 403,
                statusText: 'Forbidden'
            });
        }

        if (!response.ok) {
            throw new Response('Failed to load resource', {
                status: response.status,
                statusText: response.statusText
            });
        }

        const resource = await response.json();
        return { resource };

    } catch (error) {
        if (error instanceof Response) {
            throw error;
        }

        // Network error or other unexpected error
        throw new Response('Network error. Please check your connection.', {
            status: 500,
            statusText: 'Internal Server Error'
        });
    }
};

// Handle errors in component:
// export const ResourceErrorBoundary = () => {
//   const error = useRouteError();
//   if (isRouteErrorResponse(error)) {
//     return <div>Error {error.status}: {error.statusText}</div>;
//   }
//   return <div>Unknown error</div>;
// };

// ============================================================================
// EXAMPLE 8: Loader with Caching Strategy
// ============================================================================

const cache = new Map<string, { data: any; timestamp: number }>();
const CACHE_DURATION = 1000 * 60 * 5; // 5 minutes

export const cachedLoader = async ({ params }: LoaderFunctionArgs) => {
    const { id } = params;
    const cacheKey = `resource-${id}`;

    // Check cache
    const cached = cache.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
        return { data: cached.data, fromCache: true };
    }

    // Fetch fresh data
    const response = await fetch(`/api/resources/${id}`);
    const data = await response.json();

    // Update cache
    cache.set(cacheKey, { data, timestamp: Date.now() });

    return { data, fromCache: false };
};

// ============================================================================
// EXAMPLE 9: Prefetching Related Data
// ============================================================================

export const categoryWithRelationsLoader = async ({ params }: LoaderFunctionArgs) => {
    const { categoryId } = params;

    // Fetch main category
    const categoryResponse = await fetch(`/api/categories/${categoryId}`);
    const category = await categoryResponse.json();

    // Prefetch related data that might be needed
    const [transactions, subcategories, rules] = await Promise.allSettled([
        fetch(`/api/categories/${categoryId}/transactions`).then(r => r.json()),
        fetch(`/api/categories/${categoryId}/subcategories`).then(r => r.json()),
        fetch(`/api/categories/${categoryId}/rules`).then(r => r.json())
    ]);

    return {
        category,
        transactions: transactions.status === 'fulfilled' ? transactions.value : [],
        subcategories: subcategories.status === 'fulfilled' ? subcategories.value : [],
        rules: rules.status === 'fulfilled' ? rules.value : []
    };
};

