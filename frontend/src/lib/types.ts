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
}

export interface PerCourseUsage {
  /** Null for LLM calls from a run that failed before the course was saved. */
  course_id: number | null;
  title: string | null;
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
