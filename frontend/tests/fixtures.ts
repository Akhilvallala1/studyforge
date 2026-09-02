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
  CoursePlan,
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

/** A plan with no deadline, which is the state DeadlineForm's submit path starts from. */
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
    observed_per_week: null,
    observed_sample: 0,
    finish_projection: null,
    reason: "no_deadline",
    ...overrides,
  };
}
