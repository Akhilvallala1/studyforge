import Link from "next/link";
import { notFound } from "next/navigation";

import { ConceptMap, MasteryLegend } from "@/components/ConceptMap";
import { CourseTabs } from "@/components/CourseTabs";
import { ErrorState } from "@/components/ui/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <p className="mt-5 rounded-surface border border-line px-4 py-6 text-ui text-ink-muted">
      This course has no concepts to map yet. Concepts are listed by each lesson when the course
      is generated, so a map appears here as soon as its lessons name any.
    </p>
  );
}

const BACK_TO_COURSES_LINK = (
  <Link
    href="/courses"
    className="text-small text-ink-muted transition-colors duration-fast ease-standard hover:text-ink"
  >
    &larr; All courses
  </Link>
);

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
    // This is the last of the three pages this PR converts, and the order matters for
    // reading the sentence: on main, /courses/1, its lesson pages and this page ALL
    // re-threw and all served a blank Next 500, so the contrast being fixed is not
    // "the course page was friendly and this one was not". It is that CourseTabs links
    // here as a sibling tab, so converting the course page without this one would have
    // created that split one click wide. A genuine 404 still 404s; everything else
    // becomes the same inline message the other seven fetching pages show. See
    // courses/page.tsx for the 200-vs-500 reasoning.
    if (err instanceof ApiError && err.status === 404) notFound();
    const message =
      err instanceof ApiError ? err.message : "Could not reach the server. Is the backend running?";
    return (
      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
        {BACK_TO_COURSES_LINK}
        {/*
          The fetch failed, so the real course title was never learned and PageHeader gets
          the generic "Concept map" instead of the page having no h1 at all. It is the same
          primitive the success branch below uses: the T8 restyle (PR #34) moved that branch
          onto PageHeader before this one merged, so on THIS page the two branches differ in
          their heading text and in nothing else.

          That last part is specific to this page, so do not generalise it. Every error
          branch in this batch uses PageHeader with a generic title, but the LESSON page's
          success branch still hand-rolls its own h1 next to MarkCompleteButton, and its
          own comment says so: there, the two branches differ in their primitive as well as
          their text.
        */}
        <PageHeader className="mt-4" title="Concept map" />
        <ErrorState className="mt-8" message={message} />
      </main>
    );
  }

  const { concepts, lessons, weakest } = data;
  const studied = concepts.filter((concept) => concept.bucket !== "not_started").length;

  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-12">
      {BACK_TO_COURSES_LINK}

      <PageHeader className="mt-4" title={data.title} />

      <CourseTabs courseId={data.course_id} active="concepts" />

      <p className="mt-5 max-w-xl text-ui text-ink-muted">
        Concepts grouped by the lesson that teaches them, sized by how often they come up and
        filled by your current mastery. Reading left to right is the order the course teaches
        them.
      </p>

      {concepts.length === 0 || lessons.length === 0 ? (
        <ConceptsEmptyState />
      ) : (
        <>
          {/*
            The map is a figure, not prose, so it is allowed out of the reading column.
            A four-lesson course is 848px against a 768px column, which on a laptop cut
            the last lesson off mid-word for no reason: there was room on either side of
            the page the whole time. The step out is a fixed number of pixels rather than
            anything viewport-derived, so it cannot overshoot into a horizontal page
            scrollbar. Below lg it does not apply at all, which is what keeps a phone
            scrolling the map inside its own box instead of scrolling the page sideways.
          */}
          <div className="lg:-mx-28 xl:-mx-40">
            <ConceptMap lessons={lessons} concepts={concepts} courseTitle={data.title} />
          </div>
          <MasteryLegend />

          {weakest ? (
            <section className="mt-6 flex items-center justify-between gap-5 rounded-surface border border-line px-5 py-4">
              <div>
                {/*
                  Scoped in the heading, not only in the sentence under it. Only
                  concepts with a scheduled card are ranked, so "your weakest concept"
                  unqualified would claim a comparison across the whole course that was
                  never made.
                */}
                <h2 className="text-subtitle">
                  {weakest.concept_label} is the weakest concept you have studied so far
                </h2>
                <p className="mt-1 text-small text-ink-muted">{weakestExplanation(weakest)}</p>
              </div>
              <Link
                href={`/courses/${data.course_id}/lessons/${weakest.lesson_id}`}
                className="shrink-0 whitespace-nowrap rounded-control bg-fill px-4 py-2 text-small font-medium text-on-fill transition-colors duration-fast ease-standard hover:bg-fill-hover"
              >
                Study this
              </Link>
            </section>
          ) : (
            <p className="mt-6 rounded-surface border border-line px-5 py-4 text-small text-ink-muted">
              Nothing here has been scheduled for review yet, so there is no weakest concept to
              name. Finish a lesson and answer its quiz, and its concepts start earning a colour.
            </p>
          )}

          {/*
            ink-muted, not ink-subtle. The raw classes here were text-zinc-500 in both modes,
            measuring 4.83:1 light and 4.10:1 dark, so the dark value was under the 4.5 floor
            this text size needs. ink-muted takes both to 7.72:1 and 7.55:1, an improvement in
            BOTH modes rather than only dark. Do not "simplify" this to ink-subtle: it is the
            lower-contrast of the two ink tokens, and globals.css carries its measured figures.
          */}
          <p className="mt-4 text-xs text-ink-muted">
            {studied} of {concepts.length} concepts have been studied at least once.
          </p>
        </>
      )}
    </main>
  );
}
