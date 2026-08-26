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

export interface GenerateResult {
  id: number;
  title: string;
}

export interface CompleteResult {
  id: number;
  completed: boolean;
}
