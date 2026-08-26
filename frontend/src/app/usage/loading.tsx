export default function UsageLoading() {
  return (
    <main className="mx-auto w-full max-w-4xl flex-1 px-6 py-12">
      <div className="flex items-center gap-3 text-zinc-600 dark:text-zinc-400">
        <span
          aria-hidden
          className="h-5 w-5 shrink-0 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100"
        />
        <p>Loading usage data...</p>
      </div>
    </main>
  );
}
