import Link from "next/link";
import { GUIDES } from "@/lib/guides";

export const metadata = { title: "Guides · GreenTokens" };

export default function Guides() {
  return (
    <article className="max-w-3xl space-y-6 leading-7">
      <header className="border-b pb-4">
        <h1 className="text-3xl font-semibold">Guides</h1>
        <p className="mt-2 text-neutral-600">These pages are the project&apos;s own README files, so they stay in sync with the code you get from Git.</p>
      </header>
      <ul className="space-y-3">
        {GUIDES.map((g) => (
          <li key={g.slug}>
            <Link href={`/docs/${g.slug}`} className="block rounded border bg-white p-4 hover:bg-neutral-50 focus-visible:outline-2 focus-visible:outline-emerald-700">
              <span className="font-semibold text-emerald-800">{g.title}</span>
              <span className="mt-1 block text-sm text-neutral-600">{g.summary}</span>
              <span className="mt-1 block font-mono text-xs text-neutral-500">{g.file}</span>
            </Link>
          </li>
        ))}
      </ul>
    </article>
  );
}
