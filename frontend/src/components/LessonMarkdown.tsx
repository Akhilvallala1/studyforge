import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/* react-markdown without rehype-raw: raw HTML in the source stays escaped text,
   so model-generated content can't inject markup. */
export function LessonMarkdown({ content }: { content: string }) {
  return (
    <article className="prose-headings:font-semibold flex flex-col gap-4 leading-7 [&_a]:underline [&_blockquote]:border-l-2 [&_blockquote]:border-zinc-300 [&_blockquote]:pl-4 [&_blockquote]:text-zinc-600 dark:[&_blockquote]:border-zinc-700 dark:[&_blockquote]:text-zinc-400 [&_code]:rounded [&_code]:bg-zinc-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-sm dark:[&_code]:bg-zinc-800 [&_h1]:text-2xl [&_h2]:text-xl [&_h3]:text-lg [&_li]:ml-5 [&_ol]:list-decimal [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-zinc-100 [&_pre]:p-4 dark:[&_pre]:bg-zinc-800 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:w-full [&_td]:border [&_td]:border-zinc-200 [&_td]:px-3 [&_td]:py-1.5 dark:[&_td]:border-zinc-700 [&_th]:border [&_th]:border-zinc-200 [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left dark:[&_th]:border-zinc-700 [&_ul]:list-disc">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </article>
  );
}
