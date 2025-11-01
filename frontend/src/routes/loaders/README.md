# Route Loaders

This directory contains loader functions for data router routes.

## What are Loaders?

Loaders are functions that run **before** a route component renders. They:
- Fetch data needed by the route
- Can check authentication
- Can redirect users
- Run on navigation (before component mounts)

## Creating a Loader

```typescript
// exampleLoader.ts
import { LoaderFunctionArgs } from 'react-router-dom';

export const myRouteLoader = async ({ params, request }: LoaderFunctionArgs) => {
  // 1. Extract route params
  const { id } = params;
  
  // 2. Parse URL search params if needed
  const url = new URL(request.url);
  const filter = url.searchParams.get('filter');
  
  // 3. Fetch data (can be async)
  const data = await fetchMyData(id, filter);
  
  // 4. Return data - will be available via useLoaderData()
  return { data, filter };
};
```

## Using a Loader

### 1. Add to route config

```typescript
// routes/router.tsx
import { myRouteLoader } from './loaders/exampleLoader';

{
  path: 'my-route/:id',
  element: <MyPage />,
  loader: myRouteLoader
}
```

### 2. Access data in component

```typescript
// pages/MyPage.tsx
import { useLoaderData } from 'react-router-dom';

const MyPage = () => {
  const { data, filter } = useLoaderData() as { data: MyData; filter: string };
  
  return <div>{data.name}</div>;
};
```

## Best Practices

1. **Keep loaders thin** - They should fetch data, not transform it
2. **Return typed data** - Use TypeScript interfaces for better safety
3. **Handle errors** - Throw Response objects for error handling
4. **Use React Query** - For caching and advanced data management
5. **Avoid side effects** - Loaders should be pure data fetchers

## Examples

See `exampleLoaders.ts` for complete examples of:
- Simple data fetching
- Authentication checks
- Error handling
- React Query integration
- Conditional loading

