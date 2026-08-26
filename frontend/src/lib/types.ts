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

export interface QuizItem {
  id: number;
  question: string;
  kind: "mcq" | "short";
  options: string[];
  concept: string;
}

export interface LessonDetail {
  id: number;
  title: string;
  /** Markdown source rendered by the lesson view. */
  content: string;
  concepts: string[];
  completed: boolean;
  quiz: QuizItem[];
}

export interface AnswerResult {
  correct: boolean;
  expected: string;
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
}
