# Data Router Quick Start Guide

## 🚀 You Now Have Data Router!

Your app has been migrated to use React Router's data router. Here's what you need to know.

---

## ✅ What Works Now

1. **Native `useMatches()`** - No custom hooks needed
2. **Route Loaders** - Fetch data before rendering
3. **Route Actions** - Handle form submissions at route level
4. **Better Auth** - Auth checks via loaders, auto-redirects
5. **Data Callbacks** - Exactly what you asked for!

---

## 🎯 Quick Examples

### Fetch Data Before Rendering

```typescript
// In routes/router.tsx
{
  path: 'accounts/:accountId',
  element: <AccountPage />,
  loader: async ({ params }) => {
    const account = await fetch(`/api/accounts/${params.accountId}`).then(r => r.json());
    return { account };
  }
}

// In AccountPage.tsx
import { useLoaderData } from 'react-router-dom';

const AccountPage = () => {
  const { account } = useLoaderData() as { account: Account };
  return <div>{account.name}</div>;
};
```

### Warn About Unsaved Changes

```typescript
import { useBlocker } from 'react-router-dom';

const EditPage = () => {
  const [hasChanges, setHasChanges] = useState(false);
  
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      hasChanges && currentLocation.pathname !== nextLocation.pathname
  );

  useEffect(() => {
    if (blocker.state === 'blocked') {
      if (window.confirm('Discard unsaved changes?')) {
        blocker.proceed();
      } else {
        blocker.reset();
      }
    }
  }, [blocker]);

  // ... rest of component
};
```

### Save Data on Route Change

```typescript
// In your loader
export const myLoader = async ({ params }) => {
  // Called BEFORE entering the route
  console.log('About to load:', params.id);
  
  // Save any pending data here
  await savePendingChanges();
  
  // Then fetch new data
  const data = await fetchData(params.id);
  return { data };
};
```

---

## 📚 Where to Learn More

| What | Where |
|------|-------|
| Complete migration guide | `docs/data-router-migration.md` |
| 9 loader examples | `frontend/src/routes/loaders/exampleLoaders.ts` |
| Loader patterns | `frontend/src/routes/loaders/README.md` |
| This summary | `docs/MIGRATION_SUMMARY.md` |

---

## 🔄 Rollback (If Needed)

⚠️ **BrowserRouter backup files have been removed** - migration is complete!

If rollback is absolutely necessary, you would need to restore files from git history. See `docs/data-router-migration.md` for details.

However, the data router provides significant benefits and rollback is not recommended.

---

## 🎓 Next Steps

1. **Test the app** - Navigate around, check auth flow
2. **Add loaders** - Start with your most-visited routes
3. **Implement unsaved changes** - Use `useBlocker` in edit forms
4. **Add error boundaries** - Better error handling per route
5. **Read the examples** - `frontend/src/routes/loaders/exampleLoaders.ts`

---

## 💡 Pro Tips

- **Start simple** - Add loaders one route at a time
- **Use TypeScript** - Type your loader return values
- **Integrate React Query** - Use `ensureQueryData` in loaders
- **Handle errors** - Throw `Response` objects for proper error handling
- **Test auth** - Logout and verify redirect to `/login` works

---

## ❓ Common Questions

**Q: Do I have to use loaders?**  
A: No! Your app works fine without them. Add them when you need the benefits.

**Q: Can I still use React Query?**  
A: Yes! Loaders work great with React Query. See example 4 in `exampleLoaders.ts`.

**Q: What if a loader fails?**  
A: Add an `errorElement` to the route. It'll catch errors and show a fallback UI.

**Q: How do I prefetch data?**  
A: Use `<Link prefetch>` or `router.preload()` in your loader.

---

**Status: ✅ READY TO USE**

Build passes, TypeScript happy, app ready to test!

