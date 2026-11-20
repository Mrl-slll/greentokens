import Link from "next/link";

const code = "overflow-x-auto rounded border bg-neutral-100 p-4 text-sm leading-7";
const button = "inline-block rounded border border-neutral-300 bg-white px-4 py-2 text-sm hover:bg-neutral-100";

export default function Home() {
  return <article className="max-w-2xl space-y-6 leading-7">
    <header className="border-b pb-4">
      <h1 className="text-3xl font-semibold">GreenTokens</h1>
      <p className="mt-2 text-neutral-600">Get the project. Keep it updated. Open your jobs.</p>
    </header>

    <Link href="/docs/setup" className="block rounded border border-emerald-200 bg-emerald-50 p-4 hover:bg-emerald-100 focus-visible:outline-2 focus-visible:outline-emerald-700">
      <span className="font-semibold text-emerald-900">New here? Read the Setup &amp; Git guide →</span>
      <span className="mt-1 block text-sm text-emerald-900">Install Git, get the code, everyday Git commands, and run GreenTokens on the ThinkPad and the Mac.</span>
    </Link>

    <section className="space-y-3">
      <h2 className="text-lg font-semibold">Already have the project?</h2>
      <p>Open its existing folder in VS Code and use the terminal there. You do not need to clone it again.</p>
      <p className="text-sm text-neutral-600">Check your local changes:</p>
      <pre className={code}><code>git status</code></pre>
      <p className="text-sm text-neutral-600">Get updates from GitHub:</p>
      <pre className={code}><code>git pull --ff-only</code></pre>
    </section>

    <details className="rounded border bg-white p-4">
      <summary className="cursor-pointer font-medium">First time on this computer? Get the code</summary>
      <p className="my-3 text-sm">Run this once in the folder where you want to keep the project, then open the downloaded greentokens folder in VS Code.</p>
      <pre className={code}><code>git clone https://github.com/Mrl-slll/greentokens.git</code></pre>
    </details>

    <section className="space-y-3 border-t pt-5">
      <h2 className="text-lg font-semibold">Use the app</h2>
      <div className="flex flex-wrap gap-3">
        <Link className={button} href="/jobs">Open a job</Link>
        <Link className={button} href="/jobs/new">Test connection</Link>
        <Link className={button} href="/settings">Settings</Link>
      </div>
      <p className="text-sm text-neutral-600">For real jobs, choose Live in Settings and use the same identity you submitted with. Keep the local backend running.</p>
    </section>

    <footer className="border-t pt-4 text-sm text-neutral-600">
      <p>Git downloads and updates code; it does not start training.</p>
      <p>When you need the training steps, read the <Link className="underline" href="/docs/quickstart">developer quickstart</Link> or see <Link className="underline" href="/train">Train AI model</Link>.</p>
    </footer>
  </article>;
}
