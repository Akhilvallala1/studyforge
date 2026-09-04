/**
 * Builders for the payloads the components under test are fed.
 *
 * The same job conftest.py's stub providers do for the backend suite: one place that
 * knows what a well-formed row looks like, so a test that cares about one field says
 * only that field and a schema change breaks these builders rather than thirty
 * object literals.
 *
 * Everything here is typed against lib/types, deliberately: a fixture that drifts from
 * the wire contract should fail tsc, not quietly render a component into a state the
 * server can never produce.
 */

import type { TutorOutcome } from "@/lib/api";
import type {
  AnswerResult,
  AttemptState,
  CoursePlan,
  QuizItem,
  QuizProgress,
  TutorConversation,
  TutorGuided,
  TutorLimits,
  TutorMessage,
  TutorTurn,
} from "@/lib/types";

/** A promise resolved by the test, so a request can be held in flight deliberately. */
export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

export const LIMITS: TutorLimits = {
  concept_used: 1,
  concept_limit: 10,
  day_used: 1,
  day_limit: 30,
  resets_at: "2026-09-02T04:00:00Z",
};

export const GUIDED: TutorGuided = { run: 0, run_max: 2, available: true };

type TutorRow = Extract<TutorMessage, { role: "tutor" }>;

/**
 * A tutor reply row. `answer` is always present, the way the server guarantees; the
 * optional registers default to null so each test states exactly the shape it drives.
 */
export function tutorRow(fields: {
  id?: number;
  answer: string;
  beyond?: string | null;
  ask?: string | null;
  check?: string | null;
}): TutorRow {
  return {
    role: "tutor",
    id: fields.id ?? 2,
    content: null,
    answer: fields.answer,
    beyond: fields.beyond ?? null,
    ask: fields.ask ?? null,
    check: fields.check ?? null,
    model: "tutor-model",
    created_at: "2026-09-01T12:00:05Z",
  };
}

export function learnerRow(content: string, id = 1): TutorMessage {
  return {
    role: "learner",
    id,
    content,
    answer: null,
    beyond: null,
    check: null,
    ask: null,
    model: null,
    created_at: "2026-09-01T12:00:00Z",
  };
}

export function conversation(messages: TutorMessage[]): TutorConversation {
  return {
    concept_key: "stability",
    concept_label: "Stability",
    messages,
    last_message_at: messages.length ? "2026-09-01T12:00:05Z" : null,
    limits: LIMITS,
    guided: GUIDED,
  };
}

/** What a successful POST hands back: the two rows just written, nothing else. */
export function turnOutcome(reply: TutorRow, question = "What grows stability?"): TutorOutcome {
  const turn: TutorTurn = {
    concept_key: "stability",
    concept_label: "Stability",
    learner: learnerRow(question, reply.id - 1),
    reply,
    limits: LIMITS,
    mode: reply.ask ? "guided" : "answer",
    guided: GUIDED,
  };
  return { kind: "turn", turn };
}

/**
 * A plan with no deadline, which is the state DeadlineForm's submit path starts from.
 *
 * THE PACE FIELDS ARE MEASURED RATHER THAN EMPTY, and the choice is deliberate even
 * though nothing asserts on them today: DeadlineForm reads only course_id, deadline and
 * deadline_label, so every pace value here is currently structural. That is exactly why
 * they should describe an ordinary learner. A future test that renders the whole plan
 * screen off this base gets the path with the most logic in it, the two rates and the
 * share sentence and a projected date, rather than a screen of dashes that exercises the
 * degenerate branch and looks like it passed.
 *
 * THE NUMBERS ARE INTERNALLY CONSISTENT, which matters more than any single value,
 * because a fixture is also documentation of a shape the server can actually produce:
 *   - 10 total and 6 remaining means 4 lessons finished here, so the per-course rate is
 *     4 over the 30-day window, 0.93 a week.
 *   - 12 completions across every course clears the server's five-completion minimum, so
 *     both rates are non-null. Below it the server nulls BOTH, and a fixture with one set
 *     and the other null would be a payload the backend never sends.
 *   - The two rates DIFFER, so the share sentence renders rather than the "all of that"
 *     equality branch, which is the case this feature exists for.
 *   - 6 remaining at 0.93 a week is 45 days, which is where finish_projection lands, and
 *     projection_reason is null because a date exists. A deadline is not required for a
 *     projection, so a null deadline sits with a real date quite legitimately.
 */
/** No attempts yet, the state `restored` builds for an item the learner has not touched. */
export const UNANSWERED: AttemptState = {
  attempts: 0,
  first_attempt_correct: null,
  ever_correct: false,
  latest_quiz_attempt: null,
};

/**
 * One quiz item. `options` defaults to a plausible mcq set for an mcq item and to an
 * empty array otherwise, matching what the server sends for a short-answer item.
 */
export function quizItem(fields: { id: number; kind: "mcq" | "short" } & Partial<QuizItem>): QuizItem {
  return {
    id: fields.id,
    question: fields.question ?? "Which orbit shape keeps a satellite's altitude constant?",
    kind: fields.kind,
    options: fields.options ?? (fields.kind === "mcq" ? ["Circular", "Elliptical", "Parabolic"] : []),
    concept: fields.concept ?? "orbital-stability",
    attempt_state: fields.attempt_state ?? UNANSWERED,
  };
}

export function quizProgress(overrides: Partial<QuizProgress> = {}): QuizProgress {
  return { items: 1, answered: 0, correct: 0, first_try_correct: 0, ...overrides };
}

/**
 * What POSTing a quiz answer hands back. `everCorrect` defaults to this attempt's own
 * verdict, but is its own parameter because it can disagree: an item solved on an
 * earlier attempt stays `ever_correct` even when this one is wrong.
 */
export function answerResult(fields: {
  correct: boolean;
  expected: string;
  everCorrect?: boolean;
}): AnswerResult {
  return {
    correct: fields.correct,
    expected: fields.expected,
    attempt_id: 1,
    attempt_no: 1,
    attempt_state: {
      attempts: 1,
      first_attempt_correct: fields.correct,
      ever_correct: fields.everCorrect ?? fields.correct,
      latest_quiz_attempt: {
        answer: "the learner's submitted answer",
        correct: fields.correct,
        expected: fields.expected,
        created_at: "2026-09-01T12:00:05Z",
      },
    },
  };
}

export function plan(overrides: Partial<CoursePlan> = {}): CoursePlan {
  return {
    course_id: 1,
    title: "Course",
    deadline: null,
    deadline_label: null,
    status: "none",
    days_until: null,
    available_days: null,
    days_off_in_window: null,
    lessons_total: 10,
    lessons_remaining: 6,
    required_per_week: null,
    observed_per_week_all_courses: 2.8,
    observed_sample_all_courses: 12,
    observed_per_week_this_course: 0.9333333333333333,
    finish_projection: "2026-10-16",
    reason: "no_deadline",
    projection_reason: null,
    ...overrides,
  };
}
