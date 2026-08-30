import Link from "next/link";
import { notFound } from "next/navigation";

import { ConceptMap, MasteryLegend } from "@/components/ConceptMap";
import { CourseTabs } from "@/components/CourseTabs";
import { ApiError, getCourseConcepts } from "@/lib/api";
import type { CourseConcepts, WeakestConcept } from "@/lib/types";

export const dynamic = "force-dynamic";

/**
 * Written from `weakest.reason` rather than hardcoded, so the sentence stays true if
 * the server ever ranks by something other than stability. An unrecognised reason says
 * only that the concept was flagged: better a thin sentence than a confident wrong one.
 */
function weakestExplanation(weakest: WeakestConcept): string {
  const taught = `It is introduced in ${weakest.lesson_title}.`;
  if (weakest.reason === "lowest_stability") {
    return `Of everything you have studied in this course, this is the concept your memory is least likely to still be holding. ${taught}`;
  }
  return `This is the concept in the course most worth your attention right now. ${taught}`;
}

function ConceptsEmptyState() {
  return (
    <p className="mt-5 rounded-lg border border-zinc-200 px-4 py-6 text-sm text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
      This course has no concepts to map yet. Concepts are listed by each lesson when the course
      is generated, so a map appears here as soon as its lessons name any.
    </p>
  );
}

export default async function CourseConceptsPage(
  props: PageProps<"/courses/[courseId]/concepts">,
) {
  const { courseId } = await props.params;
  const id = Number(courseId);
  if (!Number.isInteger(id)) notFound();

  let data: CourseConcepts;
  try {
    data = await getCourseConcepts(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  const { concepts, lessons, weakest } = data;
  const studied = concepts.filter((concept) => concept.bucket !== "not_started").length;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      <Link
        href="/courses"
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; All courses
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">{data.title}</h1>

      <CourseTabs courseId={data.course_id} active="concepts" />

      <p className="mt-5 max-w-xl text-sm leading-relaxed text-zinc-600 dark:text-zinc-400">
        Concepts grouped by the lesson that teaches them, sized by how often they come up and
        filled by your current mastery. Reading left to right is the order the course teaches
        them.
      </p>

      {concepts.length === 0 || lessons.length === 0 ? (
        <ConceptsEmptyState />
      ) : (
        <>
          <ConceptMap lessons={lessons} concepts={concepts} courseTitle={data.title} />
          <MasteryLegend />

          {weakest ? (
            <section className="mt-6 flex items-center justify-between gap-5 rounded-lg border border-zinc-200 px-5 py-4 dark:border-zinc-800">
              <div>
                <h2 className="text-[15px] font-semibold">
                  {weakest.concept_label} is your weakest concept
                </h2>
                <p className="mt-1 text-[13px] text-zinc-600 dark:text-zinc-400">
                  {weakestExplanation(weakest)}
                </p>
              </div>
              <Link
                href={`/courses/${data.course_id}/lessons/${weakest.lesson_id}`}
                className="shrink-0 whitespace-nowrap rounded-lg bg-zinc-900 px-4 py-2 text-[13px] font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
              >
                Study this
              </Link>
            </section>
          ) : (
            <p className="mt-6 rounded-lg border border-zinc-200 px-5 py-4 text-[13px] text-zinc-600 dark:border-zinc-800 dark:text-zinc-400">
              Nothing here has been scheduled for review yet, so there is no weakest concept to
              name. Finish a lesson and answer its quiz, and its concepts start earning a colour.
            </p>
          )}

          <p className="mt-4 text-xs text-zinc-500 dark:text-zinc-500">
            {studied} of {concepts.length} concepts have been studied at least once.
          </p>
        </>
      )}
    </main>
  );
}
