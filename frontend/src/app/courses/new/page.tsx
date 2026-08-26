import Link from "next/link";

import { GenerateForm } from "@/components/GenerateForm";

export default function NewCoursePage() {
  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-12">
      <Link
        href="/"
        className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100"
      >
        &larr; All courses
      </Link>
      <h1 className="mt-4 text-3xl font-semibold tracking-tight">Create a course</h1>
      <p className="mt-1 text-zinc-600 dark:text-zinc-400">
        Paste your material, point at a web page, or upload a PDF.
      </p>
      <div className="mt-8">
        <GenerateForm />
      </div>
    </main>
  );
}
