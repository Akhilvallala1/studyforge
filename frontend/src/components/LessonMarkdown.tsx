import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Loose comparison so wording that differs only in case, spacing, or emphasis still matches. */
function normalizeHeading(text: string): string {
  return text
    .replace(/[*_`]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

/**
 * Generated lessons usually open with "# <title>", which renders a second h1 below
 * the page's own title. Drop that opening heading when it repeats the title, and
 * leave one that says something different.
 */
export function stripDuplicateTitle(content: string, title: string): string {
  const wanted = normalizeHeading(title);
  if (!wanted) return content;

  const lines = content.split(/\r?\n/);
  let start = 0;
  while (start < lines.length && lines[start].trim() === "") start += 1;
  if (start >= lines.length) return content;

  const first = lines[start];
  const atx = /^#\s+(.*?)\s*#*$/.exec(first);
  const underlined = /^=+\s*$/.test(lines[start + 1] ?? "") && first.trim() !== "";

  let heading: string | null = null;
  let consumed = 0;
  if (atx) {
    heading = atx[1];
    consumed = start + 1;
  } else if (underlined) {
    heading = first;
    consumed = start + 2;
  }

  if (heading === null || normalizeHeading(heading) !== wanted) return content;

  const rest = lines.slice(consumed);
  while (rest.length > 0 && rest[0].trim() === "") rest.shift();
  return rest.join("\n");
}

/*
 * react-markdown without rehype-raw: raw HTML in the source stays escaped text, so
 * model-generated content can't inject markup.
 *
 * text-prose, not text-ui: globals.css's type scale calls it out by name as "Lesson
 * markdown body only", so this is the one place in the app it belongs. It replaces
 * the raw 1.75rem line-height utility the article carried before; its font-size
 * (1rem) is what that class left implicit, and its own 1.625rem line-height
 * tightens the body leading by about 7% as a side effect. That utility is named by
 * its value rather than spelled out, because Tailwind v4's scanner reads comments
 * and would emit a real rule for a class this file no longer uses. An earlier
 * revision spelled it out in the clause just above, contradicting this very
 * sentence, and shipped no dead rule only because the punctuation it sat against
 * made the scanner reject the candidate: measured, the class between spaces IS
 * emitted and the same class followed by a comma is not. That is luck, not a rule
 * to lean on, so keep naming it by its value.
 *
 * Headings map onto the app's named scale rather than the raw text-2xl/xl/lg the prior
 * version used: [&_h1]:text-title and [&_h2]:text-subtitle both bake their own
 * font-weight (600) into the token, the same way PageHeader's own <h1 className=
 * "text-display"> needs no separate font-semibold. There is no third named HEADING step
 * below subtitle (text-ui is a UI-chrome step, and is smaller than body text, which is
 * the whole trap described below), so h3 takes an explicit font-semibold and no size
 * class at all, inheriting the article's text-prose 1rem, instead of inventing a new
 * token for one selector.
 * The missing size utility is deliberate and load-bearing: preflight sets h1..h6 {
 * font-size: inherit }, so an h3 with no font-size class lands exactly on body size,
 * whereas either neighbouring step would be wrong in one direction (text-ui is
 * 0.9375rem, BELOW the paragraphs the heading introduces; text-subtitle is 1.0625rem
 * and is h2's). An earlier revision of this PR did put the ui step on h3 through an
 * arbitrary variant and shipped the heading one notch smaller than its own body text,
 * so do not add a size class back here without re-reading this. (That variant is
 * described rather than written out for the same scanner reason as above.)
 *
 * `prose-headings:font-semibold`, which sat on the <article> below covering h1 through
 * h6 uniformly, is dropped along with that size utility: this app has no
 * @tailwindcss/typography plugin (see package.json), so `prose-*` was never a real
 * Tailwind variant here and the built CSS confirms it emitted no rule.
 *
 * [&_a]:text-accent is new: globals.css names "inline text links" as one of the
 * accent's three sanctioned uses, and Tailwind's preflight resets `a { color: inherit
 * }`, so a prose link previously rendered in plain ink with only the underline to mark
 * it as a link. This is the first page in the redesign with actual inline links inside
 * a paragraph, so the case had not come up yet.
 *
 * [&_code]/[&_pre] move from raw zinc-100/zinc-800 to bg-surface-sunken (zinc-50/
 * zinc-900): one step lighter/darker than the old raw values, converging onto the same
 * "recessed panel" token Badge's neutral tone and ReteachConcept's callout already use,
 * rather than keeping a third, off-scale shade around for code alone.
 *
 * [&_td]/[&_th] move to border-line rather than border-line-strong: a table gridline is
 * a divider, not a control boundary (see Button.tsx's comment on why its own secondary
 * variant needs the stronger step), and border-line is where MOST dividers in the app
 * already sit: the plan page's section rule, the Today page's rule beneath the Review
 * session heading, CostBanner, CourseTabs, SiteHeader, DaysOffControl, the ReviewSession
 * component's own four, and the body rows of both tables on the usage page. An earlier
 * draft of this list said "the plan and courses section rules". The courses page draws no
 * rule of its own: the one border class in courses/page.tsx is a Card hover tint, which
 * recolours a border Card itself supplies rather than adding one. The rule that entry was
 * reaching for is the Today page's, in app/page.tsx, on the div that holds the "Review
 * session" heading.
 *
 * Most, not every, and the exception is the nearest analogue there is. Those two usage
 * tables draw their HEADER rule at border-line-strong, on the tr inside each thead,
 * while their body rows take border-line, so that table splits the two steps on
 * purpose. Two things make the split wrong to copy here. Those tables draw horizontal
 * row rules only, where [&_td]:border boxes every cell on all four sides, so the same
 * token lands several times more often per row and the heavier one would read as chrome
 * around the content rather than as structure within it. And their header rule separates
 * an uppercase text-micro label row from the data below it, where a lesson table's
 * header cells are content in the same voice as its body. Anyone who does want a header
 * rule back should take the usage page's split rather than raise every cell.
 *
 * This is not colour-neutral in both modes, so it is worth saying plainly: light is
 * unchanged (#e4e4e7 either way), but dark moves from 1.90:1 to 1.33:1 against the
 * surface. Deliberate, on the divider argument above.
 */
export function LessonMarkdown({ content, title }: { content: string; title: string }) {
  return (
    <article className="flex flex-col gap-4 text-prose [&_a]:text-accent [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-line-strong [&_blockquote]:pl-4 [&_blockquote]:text-ink-muted [&_code]:rounded [&_code]:bg-surface-sunken [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-small [&_h1]:text-title [&_h2]:text-subtitle [&_h3]:font-semibold [&_li]:ml-5 [&_ol]:list-decimal [&_pre]:overflow-x-auto [&_pre]:rounded-control [&_pre]:bg-surface-sunken [&_pre]:p-4 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:w-full [&_td]:border [&_td]:border-line [&_td]:px-3 [&_td]:py-1.5 [&_th]:border [&_th]:border-line [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_ul]:list-disc">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {stripDuplicateTitle(content, title)}
      </ReactMarkdown>
    </article>
  );
}
