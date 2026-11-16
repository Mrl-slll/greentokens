import { isValidElement, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Link from "next/link";
import { rewriteHref } from "@/lib/guides";
import { CopyButton } from "./CopyButton";

function textOf(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (isValidElement<{ children?: ReactNode }>(node)) return textOf(node.props.children);
  return "";
}

/** Renders a repository Markdown file with the site's styles. Raw HTML in the file is not rendered. */
export function Markdown({ source, file }: { source: string; file: string }) {
  return (
    <div className="space-y-4 leading-7">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="border-b pb-3 text-3xl font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="pt-4 text-xl font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="pt-2 text-lg font-semibold">{children}</h3>,
          ul: ({ children }) => <ul className="list-disc space-y-1 pl-6">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal space-y-1 pl-6">{children}</ol>,
          blockquote: ({ children }) => <blockquote className="rounded border-l-4 border-amber-400 bg-amber-50 px-4 py-2 text-amber-950">{children}</blockquote>,
          table: ({ children }) => <div className="overflow-x-auto"><table className="w-full border-collapse text-left text-sm">{children}</table></div>,
          th: ({ children }) => <th className="border-b bg-neutral-100 p-2 font-semibold">{children}</th>,
          td: ({ children }) => <td className="border-b p-2 align-top">{children}</td>,
          code: ({ children, className }) => className
            ? <code className={className}>{children}</code>
            : <code className="rounded bg-neutral-100 px-1 py-0.5 text-[0.9em]">{children}</code>,
          pre: ({ children }) => (
            <div className="relative">
              <pre className="overflow-x-auto rounded border bg-neutral-100 p-4 pr-16 text-sm leading-6">{children}</pre>
              <CopyButton text={textOf(children).replace(/\n$/, "")} />
            </div>
          ),
          a: ({ href, children }) => {
            const target = rewriteHref(href, file);
            if (!target) return <span>{children}</span>;
            if (target.startsWith("/")) return <Link href={target} className="text-emerald-800 underline">{children}</Link>;
            return <a href={target} className="text-emerald-800 underline" target="_blank" rel="noreferrer">{children}</a>;
          },
        }}
      >
        {source}
      </ReactMarkdown>
    </div>
  );
}
