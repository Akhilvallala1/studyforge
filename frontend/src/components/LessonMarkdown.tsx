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

/* react-markdown without rehype-raw: raw HTML in the source stays escaped text,
   so model-generated content can't inject markup. */
export function LessonMarkdown({ content, title }: { content: string; title: string }) {
  return (
    <article className="prose-headings:font-semibold flex flex-col gap-4 leading-7 [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-zinc-300 [&_blockquote]:pl-4 [&_blockquote]:text-zinc-600 dark:[&_blockquote]:border-zinc-700 dark:[&_blockquote]:text-zinc-400 [&_code]:rounded [&_code]:bg-zinc-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-sm dark:[&_code]:bg-zinc-800 [&_h1]:text-2xl [&_h2]:text-xl [&_h3]:text-lg [&_li]:ml-5 [&_ol]:list-decimal [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-zinc-100 [&_pre]:p-4 dark:[&_pre]:bg-zinc-800 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:w-full [&_td]:border [&_td]:border-zinc-200 [&_td]:px-3 [&_td]:py-1.5 dark:[&_td]:border-zinc-700 [&_th]:border [&_th]:border-zinc-200 [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left dark:[&_th]:border-zinc-700 [&_ul]:list-disc">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {stripDuplicateTitle(content, title)}
      </ReactMarkdown>
    </article>
  );
}
