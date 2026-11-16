import Link from "next/link";
import { notFound } from "next/navigation";
import { Markdown } from "@/components/Markdown";
import { GUIDES, findGuide, readGuide } from "@/lib/guides";

// Only the allowlisted guides exist; any other slug is a 404.
export const dynamicParams = false;
export function generateStaticParams() {
  return GUIDES.map((g) => ({ slug: g.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }) {
  const guide = findGuide((await params).slug);
  return { title: guide ? `${guide.title} · GreenTokens` : "Guide · GreenTokens" };
}

export default async function GuidePage({ params }: { params: Promise<{ slug: string }> }) {
  const guide = findGuide((await params).slug);
  if (!guide) notFound();
  let source: string;
  try { source = await readGuide(guide); }
  catch { notFound(); }
  return (
    <article className="max-w-3xl space-y-4">
      <nav className="text-sm text-neutral-600"><Link className="underline" href="/docs">Guides</Link> / <span className="font-mono">{guide.file}</span></nav>
      <Markdown source={source} file={guide.file} />
    </article>
  );
}
