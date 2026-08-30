import type { ConceptLesson, ConceptNode, MasteryBucket } from "@/lib/types";

/**
 * The concept map: one column per lesson, in the order the course teaches them.
 *
 * There are no arrows here and there is no code to draw any, which is the point. The
 * system records no dependency between two concepts, so the only honest ordering claim
 * available is "the course teaches these left to right". Inferring prerequisites from
 * lesson order would produce confident arrows that are frequently wrong, and telling a
 * learner they are blocked on something they are not is worse than telling them
 * nothing. `edges_available` stays false server-side for the same reason.
 *
 * Laid out by hand in plain SVG. A few dozen circles in fixed columns is arithmetic,
 * not a graph layout problem, and it does not justify a charting dependency.
 */

const COLUMN_WIDTH = 212;
const COLUMN_LABEL_Y = 34;
const COLUMN_SUBLABEL_Y = 48;
const RULE_TOP = 44;
const RULE_BOTTOM_INSET = 24;
const FIRST_ROW_Y = 118;
const ROW_PITCH = 110;
const MIN_RADIUS = 22;
const MAX_RADIUS = 38;
const BOTTOM_PADDING = 40;
/** The artboard's height, kept as a floor so a small course does not render squashed. */
const MIN_HEIGHT = 360;
const MAX_LABEL_LINES = 2;

interface BucketStyle {
  fill: string;
  text: string;
  border?: string;
  /** How the bucket is named in the legend and in every accessible label. */
  label: string;
}

/**
 * Four buckets, and deliberately no "locked". See `unknownBucketFallback` for what
 * happens if a future server sends one anyway.
 */
export const BUCKET_STYLES: Record<MasteryBucket, BucketStyle> = {
  mastered: {
    fill: "var(--concept-mastered)",
    text: "var(--concept-mastered-text)",
    label: "Mastered",
  },
  solid: { fill: "var(--concept-solid)", text: "var(--concept-solid-text)", label: "Solid" },
  shaky: { fill: "var(--concept-shaky)", text: "var(--concept-shaky-text)", label: "Shaky, due soon" },
  not_started: {
    fill: "var(--concept-not-started)",
    text: "var(--concept-not-started-text)",
    border: "var(--concept-not-started-border)",
    label: "Not started",
  },
};

export const LEGEND_ORDER: MasteryBucket[] = ["mastered", "solid", "shaky", "not_started"];

/**
 * Anything the client does not recognise renders as not-started.
 *
 * The API only ever emits "locked" when it has a real prerequisite graph, which it does
 * not have. If one arrives regardless, showing it as untouched is the safe reading: it
 * understates what the learner has done, where painting a padlock would invent a gate
 * and stop them working on something nothing is actually blocking.
 */
function bucketOf(bucket: string): MasteryBucket {
  return Object.prototype.hasOwnProperty.call(BUCKET_STYLES, bucket)
    ? (bucket as MasteryBucket)
    : "not_started";
}

/**
 * Node radius from occurrence count, scaled across the course's own range so the
 * biggest and smallest concepts are always visibly different. A course where every
 * concept comes up equally often gets one uniform mid-size, which is the truth: there
 * is nothing to rank.
 */
function radiusScale(concepts: ConceptNode[]): (occurrences: number) => number {
  const counts = concepts.map((concept) => Math.max(1, concept.occurrences));
  const low = Math.min(...counts);
  const high = Math.max(...counts);
  const middle = (MIN_RADIUS + MAX_RADIUS) / 2;
  if (!counts.length || low === high) return () => middle;
  return (occurrences) => {
    const clamped = Math.min(Math.max(occurrences, low), high);
    return MIN_RADIUS + ((clamped - low) / (high - low)) * (MAX_RADIUS - MIN_RADIUS);
  };
}

function truncate(text: string, maxChars: number): string {
  return text.length <= maxChars ? text : `${text.slice(0, Math.max(1, maxChars - 3))}...`;
}

/**
 * Greedy word wrap into at most two lines that fit inside the circle. Purely visual:
 * the untruncated label is always in the node's accessible name and its tooltip, so a
 * long concept is never only half-readable.
 */
function wrapLabel(label: string, radius: number, fontSize: number): string[] {
  // A chord safely inside the circle rather than its diameter, and an average glyph
  // width for the weight used here. Approximate on purpose: SVG cannot measure text
  // server-side, and being a little conservative costs nothing.
  const maxChars = Math.max(4, Math.floor((radius * 1.7) / (fontSize * 0.55)));
  const words = label.split(/\s+/).filter(Boolean);
  if (!words.length) return [];

  const lines: string[] = [];
  let current = words[0];
  for (const word of words.slice(1)) {
    const candidate = `${current} ${word}`;
    if (candidate.length <= maxChars) {
      current = candidate;
    } else {
      lines.push(current);
      current = word;
    }
  }
  lines.push(current);

  if (lines.length > MAX_LABEL_LINES) {
    const kept = lines.slice(0, MAX_LABEL_LINES);
    kept[MAX_LABEL_LINES - 1] = truncate(`${kept[MAX_LABEL_LINES - 1]}...`, maxChars);
    return kept;
  }
  return lines.map((line) => truncate(line, maxChars));
}

interface Column {
  lesson: ConceptLesson;
  concepts: ConceptNode[];
}

function buildColumns(lessons: ConceptLesson[], concepts: ConceptNode[]): Column[] {
  const columns: Column[] = lessons.map((lesson) => ({ lesson, concepts: [] }));
  for (const concept of concepts) {
    // Defensive only: lessons and concepts come from one response, and the server
    // builds both indices from a single ordering.
    columns[concept.lesson_index]?.concepts.push(concept);
  }
  return columns;
}

function nodeDescription(concept: ConceptNode, lessonNumber: number): string {
  const bucket = BUCKET_STYLES[bucketOf(concept.bucket)].label;
  const times = concept.occurrences === 1 ? "once" : `${concept.occurrences} times`;
  return `${concept.concept_label}: ${bucket}. Taught in lesson ${lessonNumber}, comes up ${times}.`;
}

export function ConceptMap({
  lessons,
  concepts,
  courseTitle,
}: {
  lessons: ConceptLesson[];
  concepts: ConceptNode[];
  courseTitle: string;
}) {
  const columns = buildColumns(lessons, concepts);
  const radiusOf = radiusScale(concepts);

  const width = Math.max(columns.length, 1) * COLUMN_WIDTH;
  const rows = Math.max(1, ...columns.map((column) => column.concepts.length));
  const height = Math.max(
    MIN_HEIGHT,
    FIRST_ROW_Y + (rows - 1) * ROW_PITCH + MAX_RADIUS + BOTTOM_PADDING,
  );

  const title = `Concept map for ${courseTitle}`;
  const description =
    `${concepts.length} concepts in ${columns.length} lessons, grouped by the lesson that ` +
    "teaches them and coloured by mastery. No prerequisites are shown.";

  return (
    <>
      {/*
        The scroll lives here, not on the page. The map keeps its intrinsic pixel size
        rather than scaling to the viewport, because a scaled-down 848px map puts 11px
        labels below legibility on a phone. Focusable so the scroll is reachable by
        keyboard, which a plain overflow container is not.
      */}
      <div
        role="group"
        aria-label={title}
        tabIndex={0}
        className="mt-5 overflow-x-auto rounded-lg border border-zinc-200 bg-zinc-50/60 p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-zinc-500 dark:border-zinc-800 dark:bg-zinc-900/40"
      >
        <svg
          role="img"
          aria-label={`${title}. ${description}`}
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          style={{ minWidth: width }}
        >
          <title>{title}</title>
          <desc>{description}</desc>

          {/* Column separators, one between each pair of lessons. */}
          <g stroke="var(--concept-rule)" strokeWidth={1}>
            {columns.slice(1).map((column, index) => (
              <path
                key={column.lesson.id}
                d={`M ${(index + 1) * COLUMN_WIDTH} ${RULE_TOP} L ${(index + 1) * COLUMN_WIDTH} ${height - RULE_BOTTOM_INSET}`}
              />
            ))}
          </g>

          {columns.map((column, columnIndex) => {
            const centerX = columnIndex * COLUMN_WIDTH + COLUMN_WIDTH / 2;
            return (
              <g key={column.lesson.id}>
                <text
                  x={centerX}
                  y={COLUMN_LABEL_Y}
                  textAnchor="middle"
                  fontSize={11}
                  fontWeight={600}
                  fill="var(--concept-column-label)"
                >
                  {`Lesson ${columnIndex + 1}`}
                </text>
                <text
                  x={centerX}
                  y={COLUMN_SUBLABEL_Y}
                  textAnchor="middle"
                  fontSize={10}
                  fill="var(--concept-column-sublabel)"
                >
                  {truncate(column.lesson.title, 30)}
                </text>

                {column.concepts.map((concept, rowIndex) => {
                  const style = BUCKET_STYLES[bucketOf(concept.bucket)];
                  const radius = radiusOf(concept.occurrences);
                  const centerY = FIRST_ROW_Y + rowIndex * ROW_PITCH;
                  const fontSize = radius >= 32 ? 12 : 11;
                  const lineHeight = fontSize + 2;
                  const lines = wrapLabel(concept.concept_label, radius, fontSize);
                  const firstLineY =
                    centerY - ((lines.length - 1) * lineHeight) / 2 + fontSize * 0.34;

                  return (
                    <g key={concept.concept_key}>
                      {/* Hover text. The full label, since the drawn one may be clipped. */}
                      <title>{nodeDescription(concept, columnIndex + 1)}</title>
                      <circle
                        cx={centerX}
                        cy={centerY}
                        r={radius}
                        fill={style.fill}
                        stroke={style.border}
                        strokeWidth={style.border ? 1.5 : undefined}
                      />
                      {lines.map((line, lineIndex) => (
                        <text
                          key={line + lineIndex}
                          x={centerX}
                          y={firstLineY + lineIndex * lineHeight}
                          textAnchor="middle"
                          fontSize={fontSize}
                          fontWeight={600}
                          fill={style.text}
                        >
                          {line}
                        </text>
                      ))}
                    </g>
                  );
                })}
              </g>
            );
          })}
        </svg>
      </div>

      {/*
        The same map as text. ARIA inside SVG is unevenly supported, and role="img" on
        the root makes the whole drawing a single leaf node, so per-node labels there
        would be announced by nothing. This list is the version screen readers actually
        get, and it is the reason mastery is never carried by colour alone.
      */}
      <ul className="sr-only">
        {columns.map((column, columnIndex) => (
          <li key={column.lesson.id}>
            {`Lesson ${columnIndex + 1}, ${column.lesson.title}: `}
            {column.concepts.length === 0 ? (
              "no concepts."
            ) : (
              <ul>
                {column.concepts.map((concept) => (
                  <li key={concept.concept_key}>{nodeDescription(concept, columnIndex + 1)}</li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

/** The four buckets. There is no Locked entry because there is no locked state. */
export function MasteryLegend() {
  return (
    <ul className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
      {LEGEND_ORDER.map((bucket) => {
        const style = BUCKET_STYLES[bucket];
        return (
          <li
            key={bucket}
            className="flex items-center gap-2 text-xs text-zinc-600 dark:text-zinc-400"
          >
            <span
              aria-hidden
              className="inline-block h-3 w-3 rounded-full"
              style={{
                background: style.fill,
                border: style.border ? `1px solid ${style.border}` : undefined,
              }}
            />
            {style.label}
          </li>
        );
      })}
    </ul>
  );
}
