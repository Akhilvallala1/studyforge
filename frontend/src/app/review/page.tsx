import Link from "next/link";

import { ReviewSession } from "@/components/ReviewSession";
import { ApiError, getReviewQueue } from "@/lib/api";
import type { ReviewQueue } from "@/lib/types";

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Review session | StudyForge",
};

/** Matches the backend's own queue default. */
const QUEUE_LIMIT = 50;

export default async function ReviewPage() {
  let queue: ReviewQueue;
  try {
    queue = await getReviewQueue(QUEUE_LIMIT);
  } catch (err) {
    const message =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
    return (
      <main className="mx-auto w-full max-w-[720px] flex-1 px-6 py-14">
        <h1 className="text-xl font-semibold">Review session</h1>
        <p
          role="alert"
          className="mt-4 rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
        >
          {message}
        </p>
        <Link
          href="/"
          className="mt-6 inline-block text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          &larr; Back to Today
        </Link>
      </main>
    );
  }

  // The session runs entirely off this snapshot. Answers and ratings are each their
  // own durable POST, so there is nothing session-shaped to persist: reloading just
  // asks for whatever is still due.
  return <ReviewSession queue={queue} />;
}
