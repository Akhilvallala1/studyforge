import Link from "next/link";
import { notFound } from "next/navigation";

import { LessonMarkdown } from "@/components/LessonMarkdown";
import { MarkCompleteButton } from "@/components/MarkCompleteButton";
import { QuizSection } from "@/components/QuizSection";
import { ApiError, getLesson } from "@/lib/api";
import type { LessonDetail } from "@/lib/types";

export const dynamic = "force-dynamic";

export default async function LessonPage(
  props: PageProps<"/courses/[courseId]/lessons/[lessonId]">,
) {
  const { courseId, lessonId } = await props.params;
  const id = Number(lessonId);
  if (!Number.isInteger(id)) notFound();

  let lesson: LessonDetail;
  try {
    lesson = await getLesson(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <Link
        href={`/courses/${courseId}`}
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; Back to course
      </Link>

      <div className="mt-4 flex items-start justify-between gap-4">
        <h1 className="text-3xl font-semibold tracking-tight">{lesson.title}</h1>
        <MarkCompleteButton lessonId={lesson.id} completed={lesson.completed} />
      </div>

      {lesson.concepts.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {lesson.concepts.map((concept) => (
            <li
              key={concept}
              className="rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
            >
              {concept}
            </li>
          ))}
        </ul>
      )}

      <div className="mt-8">
        <LessonMarkdown content={lesson.content} />
      </div>

      {lesson.quiz.length > 0 && (
        <div className="mt-12">
          <QuizSection quiz={lesson.quiz} />
        </div>
      )}
    </main>
  );
}
