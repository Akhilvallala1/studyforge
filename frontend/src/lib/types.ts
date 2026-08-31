export interface CourseSummary {
  id: number;
  title: string;
  description: string;
}

export interface LessonSummary {
  id: number;
  title: string;
  completed: boolean;
}

export interface ModuleDetail {
  id: number;
  title: string;
  lessons: LessonSummary[];
}

export interface CourseDetail {
  id: number;
  title: string;
  description: string;
  modules: ModuleDetail[];
}

/**
 * The learner's most recent attempt at one quiz item from the lesson quiz, not from
 * a later review session. `expected` is only ever sent inside this object, so an item
 * nobody has attempted never carries its answer key.
 */
export interface LatestAttempt {
  answer: string;
  correct: boolean;
  expected: string;
  created_at: string;
}

export interface AttemptState {
  /** Attempts made from the lesson quiz itself, excluding later review sessions. */
  attempts: number;
  /** Null until the item has been attempted from the lesson quiz. */
  first_attempt_correct: boolean | null;
  /** True if any attempt was correct, counting review sessions as well as the quiz. */
  ever_correct: boolean;
  /**
   * The newest lesson-quiz attempt, not the newest activity overall. Once review
   * sessions exist, an item can be practised recently and still show an old
   * attempt here, so do not read it as "last practised".
   */
  latest_quiz_attempt: LatestAttempt | null;
}

export interface QuizProgress {
  items: number;
  answered: number;
  correct: number;
  first_try_correct: number;
}

export interface QuizItem {
  id: number;
  question: string;
  kind: "mcq" | "short";
  options: string[];
  concept: string;
  attempt_state: AttemptState;
}

export interface LessonDetail {
  id: number;
  title: string;
  /** Markdown source rendered by the lesson view. */
  content: string;
  concepts: string[];
  completed: boolean;
  /** ISO 8601 with a UTC offset, or null while the lesson is unfinished. */
  completed_at: string | null;
  quiz: QuizItem[];
  quiz_progress: QuizProgress;
}

export interface AnswerResult {
  correct: boolean;
  expected: string;
  attempt_id: number;
  attempt_no: number;
  attempt_state: AttemptState;
}

export interface GenerateRunUsage {
  run_cost_usd: number;
  total_cost_usd: number;
  alert_active: boolean;
}

export interface GenerateResult {
  id: number;
  title: string;
  usage: GenerateRunUsage;
}

export interface UsageTotals {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  /** True if any recorded call's cost is an estimate rather than a precise figure. */
  approximate: boolean;
  /**
   * Why, in the server's words: a token count was estimated, the model's price was,
   * or both. Null when nothing was approximated. The server owns this sentence
   * because only it knows which of the two causes actually applies.
   */
  approximate_note: string | null;
}

/**
 * Which kind of row this is: one course, re-teaching that no single course owns, or
 * a generation run that failed before its course could be saved.
 */
export type SpendGroup = "course" | "remediation" | "failed_run";

export interface PerCourseUsage {
  group: SpendGroup;
  /** Null for every group except "course". */
  course_id: number | null;
  title: string | null;
  /** What the leftmost column shows, for courses and non-course groups alike. */
  label: string;
  /** The group's explanation, or null for a course row, which needs none. */
  note: string | null;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
}

export interface UsageCall {
  id: number;
  created_at: string;
  provider: string;
  model: string;
  stage: string;
  course_id: number | null;
  /** Null when the provider call errored before reporting token counts. */
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost_usd: number;
  approximate: boolean;
}

export interface AlertState {
  active: boolean;
  threshold_usd: number;
  total_usd: number;
  /**
   * The cumulative spend (USD) at the time the alert was last acknowledged,
   * or null if it has never been acknowledged. NOT a boolean, despite the name:
   * use `active` to decide whether the alert currently needs attention.
   */
  acknowledged: number | null;
}

export interface LimitState {
  configured: boolean;
  limit_usd: number | null;
  reached: boolean;
}

export interface UsageSummary {
  totals: UsageTotals;
  per_course: PerCourseUsage[];
  recent_calls: UsageCall[];
  alert: AlertState;
  limit: LimitState;
}

export interface CompleteResult {
  id: number;
  completed: boolean;
  completed_at: string | null;
}

/** A concept the learner keeps losing: two or more misses in its last five ratings. */
export interface NeedsAttentionEntry {
  /** The review card behind the concept. The remediation endpoints are keyed by it. */
  card_id: number;
  concept_key: string;
  concept_label: string;
  /** Misses inside the recent window, as in "missed 3 of 4 times". */
  missed: number;
  of: number;
  /** Lifetime lapse count on the card, which spans more than the recent window. */
  lapses: number;
  /** Current recall probability, or null for a card that has never been scheduled. */
  retrievability: number | null;
  due: string | null;
  is_due: boolean;
}

export interface ReviewToday {
  /** The local YYYY-MM-DD study day, which starts at 04:00 rather than midnight. */
  date: string;
  /**
   * What a review session would serve right now. Smaller than due_today whenever a
   * card was rated Again and is sitting out its ten-minute step, so this is what
   * gates the Start review button and the "N due now" copy.
   */
  due_now: number;
  /** The whole day's workload, for the Due today tile. Includes cards not yet servable. */
  due_today: number;
  due_this_week: number;
  /**
   * Share of due reviews recalled over 30 days, or NULL below the minimum sample.
   * Render a dash when it is null: a percentage from two reviews can only read 0,
   * 50 or 100 and would swing alarmingly.
   */
  retention: number | null;
  sample_size: number;
  day_streak: number;
  estimated_minutes: number;
  /** How many of the needs-attention concepts are due right now. */
  struggling_due: number;
  needs_attention: NeedsAttentionEntry[];
}

/**
 * One concept re-explained: a restatement in plainer words and a worked example,
 * written by the model from the lesson material the learner already saw.
 */
export interface RemediationNote {
  id: number;
  concept_key: string;
  concept_label: string;
  /**
   * Markdown, generated by a model from an uploaded document, so it is untrusted.
   * Render it through LessonMarkdown, which escapes raw HTML rather than parsing it.
   */
  content: string;
  created_at: string;
  model: string;
  /** No further explanation of this concept is generated before this moment. */
  cooldown_until: string | null;
}

/**
 * Why the server would not write a new explanation. None of these is a failure.
 *
 * `note_active` and `cooldown_active` carry the explanation the learner already has.
 *
 * `generation_in_progress` means another request is inside this card's generation
 * slot right now. It carries no note, because the request holding the slot has not
 * finished writing one, so there is nothing to show yet and nothing to do but wait.
 *
 * `not_flagged` means the concept stopped being one they keep missing, and carries
 * no note either. That collision is the thing to be careful about: it and
 * `generation_in_progress` both arrive with a null note and mean opposite things,
 * one that an explanation is on its way and one that none is wanted, so they have to
 * be told apart by their code and never by whether a note came with them.
 */
/**
 * A discriminated union rather than an interface with two independent fields, so the
 * collision above is the compiler's problem instead of the reader's. Narrowing on
 * `error` types `note` as present or absent, which means a branch cannot reach an
 * explanation without having proved it has one, and a fifth code added here is a
 * type error at every switch that consumes it rather than a silent fall into
 * whichever branch happened to be last.
 */
export type RemediationConflict =
  | { error: "note_active"; message: string; note: RemediationNote }
  | { error: "cooldown_active"; message: string; note: RemediationNote }
  | { error: "generation_in_progress"; message: string; note: null }
  | { error: "not_flagged"; message: string; note: null };

export type RemediationConflictCode = RemediationConflict["error"];

/**
 * One question in a practice run. Same shape as ReviewItem, and withheld of its answer
 * key for the same reason: practice is still retrieval, and an item that arrives with
 * its answer attached tests nothing.
 */
export interface PracticeItem {
  id: number;
  question: string;
  kind: "mcq" | "short";
  options: string[];
}

/**
 * One answer already given in today's run. It carries `expected`, which is safe here
 * because the retrieval that answer key would spoil has already happened.
 */
export interface PracticeResult {
  item_id: number;
  /** Empty when the item has since been regenerated away. The attempt row outlives it. */
  question: string;
  submitted: string;
  expected: string;
  correct: boolean;
  created_at: string;
}

/** What every practice state carries, whichever of the four it is. */
interface PracticeSessionBase {
  card_id: number;
  concept_key: string;
  concept_label: string;
  answered: number;
  correct: number;
  /** Right answers that finish the run. From the server, not hardcoded in the UI. */
  target_correct: number;
  /** Answers the run may spend in total. */
  max_answers: number;
  results: PracticeResult[];
}

/**
 * Today's practice run for one concept, discriminated on `status`.
 *
 * The server partitions `reason` by `status` and the two vocabularies never cross:
 * `done` means the learner finished a run, `unavailable` means there was no run to
 * have. Encoding that partition is the point of the union. Conflating them would tell
 * a learner they completed something that never existed, and the compiler now refuses
 * to let a `done` branch read `no_items`.
 *
 * `ready` and `in_progress` stay separate members even though both carry an item,
 * because the copy genuinely differs. Deriving that difference from `answered > 0`
 * would reintroduce the shape test this union exists to forbid.
 */
export type PracticeState =
  | (PracticeSessionBase & {
      status: "ready";
      reason: null;
      item: PracticeItem;
      resets_at: null;
    })
  | (PracticeSessionBase & {
      status: "in_progress";
      reason: null;
      item: PracticeItem;
      resets_at: null;
    })
  | (PracticeSessionBase & {
      status: "done";
      reason: "target_reached" | "attempts_spent" | "pool_exhausted";
      item: null;
      /**
       * When today's run resets, which the server sends only on a finished one. Typed
       * nullable rather than required so the renderer guards it instead of trusting
       * it: the partition above is load-bearing, this field is decoration.
       */
      resets_at: string | null;
    })
  | (PracticeSessionBase & {
      status: "unavailable";
      reason: "no_note" | "no_items";
      item: null;
      resets_at: null;
    });

export type PracticeStatus = PracticeState["status"];

/**
 * What POSTing one practice answer produced. Nothing here is an assessment: no review
 * log is written, no column of the card moves, and the schedule is untouched.
 */
export interface PracticeAnswer {
  correct: boolean;
  /**
   * The reference answer, to show beside the learner's own. The grader is exact
   * case-insensitive comparison, so this is a comparison and not a verdict.
   */
  expected: string;
  submitted: string;
  attempt_id: number;
  /**
   * The run AFTER this answer. Its `item` is the next question, or null when this
   * answer ended the run. There is deliberately no separate `next` key: a second copy
   * of the next question is a copy that could disagree with this one.
   */
  state: PracticeState;
}

/**
 * Why the server would not take a practice answer. Its own union, not an extension of
 * RemediationConflict.
 *
 * RemediationConflict is switched exhaustively in exactly one place. Folding these
 * codes into it would force that switch to handle codes its endpoint can never send:
 * the exhaustiveness check would still compile, but it would stop meaning "every code
 * this endpoint can send is handled" and start meaning "every code any remediation
 * endpoint can send is mentioned somewhere". Two endpoints, two unions, two exhaustive
 * switches, composed in the component tree rather than in the type.
 *
 * Every code carries the run the answer could not join, because the only sensible
 * thing a UI can do about "not that answer" is redraw the run it should have been
 * looking at.
 */
export type PracticeConflict =
  | { error: "item_already_answered"; message: string; state: PracticeState }
  | { error: "session_complete"; message: string; state: PracticeState }
  | { error: "no_note"; message: string; state: PracticeState }
  | { error: "no_items"; message: string; state: PracticeState };

export type PracticeConflictCode = PracticeConflict["error"];

export type RatingName = "again" | "hard" | "good" | "easy";

/**
 * What one rating button would do to the card. The server computes these from the
 * real scheduler transition with fuzzing disabled, so `label` is exactly what
 * pressing the button produces. Render it verbatim rather than reformatting the
 * interval: two buttons showing the same label is normal, not a bug.
 */
export interface RatingPreview {
  rating: number;
  name: RatingName;
  interval_minutes: number;
  interval_days: number;
  label: string;
  state: string;
}

/** The question to ask for a due card. No answer key: the point is to retrieve it. */
export interface ReviewItem {
  id: number;
  question: string;
  kind: "mcq" | "short";
  options: string[];
}

export interface ReviewCard {
  card_id: number;
  concept_key: string;
  concept_label: string;
  state: string;
  due: string | null;
  lapses: number;
  retrievability: number | null;
  preview: RatingPreview[];
  /** Null when no quiz item tests this concept any more; such a card cannot be reviewed. */
  item: ReviewItem | null;
}

export interface ReviewQueue {
  /** The real backlog, which may exceed `cards.length` when the limit trims it. */
  due_total: number;
  estimated_minutes: number;
  cards: ReviewCard[];
}

export interface ReviewAnswerResult {
  correct: boolean;
  /** The reference answer, shown beside the learner's own for them to judge. */
  expected: string;
  submitted: string;
  attempt_id: number;
  suggested_rating: number | null;
  rating_v: string;
  preview: RatingPreview[];
}

/**
 * The four mastery buckets the concept map paints. There is deliberately no "locked":
 * nothing in the system records prerequisites between concepts, so nothing may claim a
 * concept is gated. `CourseConcepts.edges_available` says the same thing as a flag.
 */
export type MasteryBucket = "mastered" | "solid" | "shaky" | "not_started";

/** One column of the map: a lesson, in the order the course teaches it. */
export interface ConceptLesson {
  id: number;
  title: string;
  /** Zero-based position in course order, matching `ConceptNode.lesson_index`. */
  index: number;
}

export interface ConceptNode {
  concept_key: string;
  concept_label: string;
  bucket: MasteryBucket;
  /**
   * The lesson that INTRODUCES the concept, which is how the map picks its column.
   * Course order, not a dependency: a lower index does not mean the concept is a
   * prerequisite of anything to its right.
   */
  lesson_id: number;
  lesson_title: string;
  lesson_index: number;
  /** How many times the concept is named across the course; the map sizes nodes by it. */
  occurrences: number;
  /** Null for a concept with no scheduled card, which is every not-started one. */
  stability: number | null;
  retrievability: number | null;
  due: string | null;
  lapses: number;
}

/**
 * The concept worth attention, or null when nothing in the course has been studied
 * yet. `reason` names the comparison the server actually made, so copy is written from
 * it rather than hardcoded; an unrecognised reason falls back to claiming nothing
 * about why.
 */
export interface WeakestConcept extends ConceptNode {
  reason: string;
}

export interface CourseConcepts {
  course_id: number;
  title: string;
  /**
   * False while no prerequisite graph exists, which is always, today. While it is
   * false the map draws no arrows and must not infer any from `lesson_index`.
   */
  edges_available: boolean;
  counts: Partial<Record<MasteryBucket, number>>;
  lessons: ConceptLesson[];
  concepts: ConceptNode[];
  weakest: WeakestConcept | null;
}

export interface ReviewRatingResult {
  card_id: number;
  concept_key: string;
  state: string;
  stability: number | null;
  difficulty: number | null;
  due: string | null;
  reps: number;
  lapses: number;
  scheduled_days: number;
  interval_label: string;
}
