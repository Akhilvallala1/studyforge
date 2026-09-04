import Link from "next/link";

import { ReviewSession } from "@/components/ReviewSession";
import { ErrorState } from "@/components/ui/ErrorState";
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
        {/* title="" suppresses ErrorState's default "Something went wrong" heading: this
            screen only ever showed the one message, and the restyle must not add text
            that was not there before. */}
        <ErrorState title="" message={message} className="mt-4" />
        <Link
          href="/"
          className="mt-6 inline-block text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
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
