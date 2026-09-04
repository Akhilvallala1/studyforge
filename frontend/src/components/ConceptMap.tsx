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
 *
 * Labels sit BELOW their node rather than inside it. Inside the circle a label got
 * about six characters at the smallest radius, which turned "Consistency" and
 * "Consensus" into two identical "Cons..." stubs on real data: two different concepts
 * that look the same are worse than no label at all. Below the node a label has the
 * column's full width and is simply readable. That also puts every string on the page
 * background instead of on a saturated fill, which is what makes the contrast numbers
 * work, and it frees radius to mean only frequency.
 */

const COLUMN_WIDTH = 212;
/** Keeps wrapped labels clear of the column rules. */
const COLUMN_PADDING = 12;
const LABEL_WIDTH = COLUMN_WIDTH - COLUMN_PADDING * 2;

const COLUMN_LABEL_Y = 34;
const COLUMN_SUBLABEL_Y = 48;
const RULE_TOP = 44;
const RULE_BOTTOM_INSET = 20;

/**
 * The lesson title under each column heading wraps the same way a concept label does,
 * for the same reason: a single truncated line turned "Introduction to Spaced
 * repetition" into "Introduction to Spaced repetiti..." and there was nowhere else on
 * screen to read the rest. Two lines fit almost every real lesson title whole, and the
 * heading also carries a tooltip for the ones they do not.
 */
const SUBLABEL_FONT = 10;
const SUBLABEL_LINE_HEIGHT = 12;
const MAX_SUBLABEL_LINES = 2;

const MIN_RADIUS = 16;
const MAX_RADIUS = 34;

const LABEL_GAP = 12;
const LABEL_FONT = 12;
const LABEL_LINE_HEIGHT = 14;
const MASTERY_FONT = 10;
const MASTERY_LINE_HEIGHT = 13;
const MAX_LABEL_LINES = 2;

/**
 * How far a node's block reaches below its centre, budgeted for the worst case of two
 * label lines so that rows line up whatever their labels turn out to be.
 */
const BLOCK_BELOW_CENTER =
  MAX_RADIUS +
  LABEL_GAP +
  LABEL_FONT +
  (MAX_LABEL_LINES - 1) * LABEL_LINE_HEIGHT +
  MASTERY_LINE_HEIGHT;
const ROW_GAP = 22;
const ROW_PITCH = BLOCK_BELOW_CENTER + ROW_GAP + MAX_RADIUS;
const HEADER_GAP = 20;
const BOTTOM_PADDING = 20;
const MIN_HEIGHT = 200;

interface BucketStyle {
  fill: string;
  border?: string;
  /** How the bucket is named in the legend and in every accessible label. */
  label: string;
  /** The same state in one word, printed under each node where space is tight. */
  short: string;
}

/**
 * Four buckets, and deliberately no "locked". See `bucketOf` for what happens if a
 * future server sends one anyway.
 *
 * There is no text colour here because no text is ever drawn on these fills. Colour is
 * a redundant encoding on this map, never the only one: every node states its mastery
 * in words underneath. That matters because the palette cannot carry the distinction on
 * its own, and is not being asked to. Solid against shaky measures 1.10 luminance
 * contrast, and green against amber is the commonest confusion pair there is.
 */
export const BUCKET_STYLES: Record<MasteryBucket, BucketStyle> = {
  mastered: { fill: "var(--concept-mastered)", label: "Mastered", short: "Mastered" },
  solid: { fill: "var(--concept-solid)", label: "Solid", short: "Solid" },
  shaky: { fill: "var(--concept-shaky)", label: "Shaky, due soon", short: "Shaky" },
  not_started: {
    fill: "var(--concept-not-started)",
    border: "var(--concept-not-started-border)",
    label: "Not started",
    short: "Not started",
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
 * is nothing to rank. Radius encodes frequency and nothing else.
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

/**
 * Characters that fit in `width` at `fontSize`. Approximate on purpose: SVG text cannot
 * be measured server-side, and an average glyph width for this weight is close enough
 * when the budget is a whole column rather than the inside of a circle.
 */
function charBudget(width: number, fontSize: number): number {
  return Math.max(4, Math.floor(width / (fontSize * 0.55)));
}

function truncate(text: string, maxChars: number): string {
  return text.length <= maxChars ? text : `${text.slice(0, Math.max(1, maxChars - 3))}...`;
}

/**
 * Greedy word wrap into at most `maxLines` lines across the column's width. At 12px that
 * is roughly 28 characters a line, so ordinary concept names arrive intact. Anything
 * still too long is truncated visually only: the untruncated text is always in the
 * element's tooltip and in the text equivalent below.
 */
function wrapLabel(label: string, fontSize: number, maxLines: number): string[] {
  const maxChars = charBudget(LABEL_WIDTH, fontSize);
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

  if (lines.length > maxLines) {
    const kept = lines.slice(0, maxLines);
    kept[maxLines - 1] = truncate(`${kept[maxLines - 1]}...`, maxChars);
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
  // Wrapped once here rather than inside the column loop, because the first row of
  // nodes has to clear the TALLEST heading: a column whose title fits on one line
  // still starts its circles level with the two-line ones beside it.
  const sublabels = columns.map((column) =>
    wrapLabel(column.lesson.title, SUBLABEL_FONT, MAX_SUBLABEL_LINES),
  );
  const headerLines = Math.max(1, ...sublabels.map((lines) => lines.length));
  const firstRowY =
    COLUMN_SUBLABEL_Y + (headerLines - 1) * SUBLABEL_LINE_HEIGHT + HEADER_GAP + MAX_RADIUS;

  const height = Math.max(
    MIN_HEIGHT,
    firstRowY + (rows - 1) * ROW_PITCH + BLOCK_BELOW_CENTER + BOTTOM_PADDING,
  );

  const title = `Concept map for ${courseTitle}`;
  const description =
    `${concepts.length} concepts in ${columns.length} lessons, grouped by the lesson that ` +
    "teaches them and coloured by mastery. No prerequisites are shown.";

  return (
    <>
      {/*
        The scroll lives here, not on the page. The map keeps its intrinsic pixel size
        rather than scaling to the viewport, because a scaled-down 848px map puts 12px
        labels below legibility on a phone. Focusable so the scroll is reachable by
        keyboard, which a plain overflow container is not.

        scroll-hint-x draws an edge shadow at whichever end has content past it, and
        nothing at all when the map fits. Without it a map cut off by the viewport read
        as a rendering fault rather than as something to drag. It also owns the surface
        colour, which those shadows need as an opaque value; it is the same colour the
        label contrast figures were measured against.
      */}
      <div
        role="group"
        aria-label={title}
        tabIndex={0}
        className="scroll-hint-x mx-auto mt-5 w-fit max-w-full overflow-x-auto rounded-surface border border-line p-2"
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
                {/* Hover text on the heading, the way every node has one, in a group of
                    its own so it covers the heading and not the whole column. Without
                    it a lesson title too long for the column was readable nowhere on
                    screen: the untruncated title is in the sr-only list below, which a
                    sighted reader never sees. */}
                <g>
                  <title>{`Lesson ${columnIndex + 1}: ${column.lesson.title}`}</title>
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
                  {sublabels[columnIndex].map((line, lineIndex) => (
                    <text
                      key={line + lineIndex}
                      x={centerX}
                      y={COLUMN_SUBLABEL_Y + lineIndex * SUBLABEL_LINE_HEIGHT}
                      textAnchor="middle"
                      fontSize={SUBLABEL_FONT}
                      fill="var(--concept-column-sublabel)"
                    >
                      {line}
                    </text>
                  ))}
                </g>

                {column.concepts.map((concept, rowIndex) => {
                  const style = BUCKET_STYLES[bucketOf(concept.bucket)];
                  const radius = radiusOf(concept.occurrences);
                  const centerY = firstRowY + rowIndex * ROW_PITCH;
                  const lines = wrapLabel(concept.concept_label, LABEL_FONT, MAX_LABEL_LINES);
                  // Measured from the largest possible radius, not this node's own, so
                  // labels sit on one baseline across a row however the circles differ.
                  const textTop = centerY + MAX_RADIUS + LABEL_GAP;
                  const masteryY = textTop + LABEL_FONT + lines.length * LABEL_LINE_HEIGHT + 1;

                  return (
                    <g key={concept.concept_key}>
                      {/* Hover text, carrying the full label in case the drawn one wrapped short. */}
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
                          y={textTop + LABEL_FONT + lineIndex * LABEL_LINE_HEIGHT}
                          textAnchor="middle"
                          fontSize={LABEL_FONT}
                          fontWeight={600}
                          fill="var(--concept-label-text)"
                        >
                          {line}
                        </text>
                      ))}
                      {/*
                        Mastery in words on every node. This is the non-colour channel:
                        it is what a colour-blind sighted reader uses, and it says the
                        same thing the tooltip and the text equivalent say.
                      */}
                      <text
                        x={centerX}
                        y={masteryY}
                        textAnchor="middle"
                        fontSize={MASTERY_FONT}
                        fill="var(--concept-muted-text)"
                      >
                        {style.short}
                      </text>
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
        get. Sighted readers are covered separately, by the mastery word under each node.
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
            className="flex items-center gap-2 text-xs text-ink-muted"
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
