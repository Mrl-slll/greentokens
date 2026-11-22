import Link from "next/link";

export const metadata = { title: "Train AI model · GreenTokens" };

const STAGES = [
  { name: "Preparing dataset", computer: "AMD ThinkPad (Windows)", detail: "Validate and preprocess the images and labels." },
  { name: "Training", computer: "MacBook Air M4", detail: "Fine-tune the model. Uses Apple GPU (MPS) only if a benchmark confirms it works; otherwise CPU. The device actually used is reported." },
  { name: "Evaluating", computer: "MacBook Air M4", detail: "Character error rate on held-out images, before and after fine-tuning." },
  { name: "Saving model", computer: "Backend storage", detail: "Store the checkpoint and the evaluation report with the job." },
];

const MISSING = [
  "A trocr_finetune_v1 job type in the backend (today only sum_numbers_v1 and linear_regression_v1 exist).",
  "Stage tracking on jobs (Preparing dataset, Training, Evaluating, Saving model).",
  "Routing each stage to a specific computer, with the ThinkPad and the Mac joined to the backend's Ray cluster.",
  "Checkpoint storage: artifacts are limited to 64 KB today, and a TrOCR checkpoint is about 250 MB.",
  "Live progress (steps, loss) while the job runs; logs are only collected at the end today.",
  "An endpoint to test the trained model on a new image.",
  "A prepared, license-checked sample dataset (about 100 training images plus a separate evaluation set).",
];

const field = "w-full rounded border border-neutral-300 bg-neutral-100 px-3 py-2 text-neutral-500";

export default function TrainModel() {
  return (
    <article className="max-w-3xl space-y-8 leading-7">
      <header className="border-b pb-4">
        <h1 className="text-3xl font-semibold">Train AI model</h1>
        <p className="mt-2 text-neutral-600">Fine-tune a preset Hugging Face model on your images, follow each stage, then download and test the result.</p>
        <p role="status" className="mt-3 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-950">
          <strong>Not available yet.</strong> This page shows the planned flow. Training can&apos;t start until the backend supports it; see <a href="#missing" className="underline">what&apos;s missing</a>. Nothing here is simulated as running.
        </p>
      </header>

      <form aria-label="Training job" className="space-y-6">
        <fieldset disabled className="space-y-6">
          <section className="space-y-2">
            <h2 className="text-xl font-semibold">1. Model</h2>
            <label className="block">
              <span className="text-sm font-medium">Preset</span>
              <select className={field} defaultValue="trocr">
                <option value="trocr">microsoft/trocr-small-printed (read printed text in images)</option>
                <option value="deit">facebook/deit-tiny-patch16-224 (image classification, fallback)</option>
              </select>
            </label>
            <p className="text-sm text-neutral-600">
              <a className="underline" href="https://huggingface.co/microsoft/trocr-small-printed" target="_blank" rel="noreferrer">View TrOCR on Hugging Face</a>
              {" · "}
              <a className="underline" href="https://huggingface.co/facebook/deit-tiny-patch16-224" target="_blank" rel="noreferrer">View DeiT-tiny</a>.
              Only curated presets will be offered; custom training code is out of scope.
            </p>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold">2. Dataset</h2>
            <label className="flex items-start gap-2"><input type="radio" name="dataset" defaultChecked className="mt-1.5" /> <span>Sample signs &amp; labels: about 100 training images with matching text, plus a separate evaluation set <span className="text-sm text-neutral-500">(not prepared yet)</span></span></label>
            <label className="flex items-start gap-2"><input type="radio" name="dataset" className="mt-1.5" /> <span>Upload your own images and labels <span className="text-sm text-neutral-500">(format to be defined)</span></span></label>
          </section>

          <section className="space-y-2">
            <h2 className="text-xl font-semibold">3. Time budget</h2>
            <label className="block max-w-xs">
              <span className="text-sm font-medium">Stop training after</span>
              <select className={field} defaultValue="30">
                <option value="15">15 minutes</option>
                <option value="30">30 minutes (demo default)</option>
                <option value="60">60 minutes</option>
              </select>
            </label>
            <p className="text-sm text-neutral-600">If the budget runs out, the last valid checkpoint is saved and the job reports that it ended early. No accuracy or finish time is guaranteed.</p>
          </section>
        </fieldset>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. What will happen</h2>
          <ol className="space-y-3">
            {STAGES.map((s, i) => (
              <li key={s.name} className="rounded border bg-white p-4">
                <p className="font-semibold">Stage {i + 1}: {s.name}</p>
                <p className="text-sm text-neutral-600">Runs on: {s.computer}</p>
                <p className="text-sm">{s.detail}</p>
              </li>
            ))}
          </ol>
          <p className="text-sm text-neutral-600">The two computers do <strong>separate stages</strong>; this is not synchronized training across both. The job page will show each stage&apos;s real computer name, device, elapsed time, training steps and loss. No invented percentages or GPU usage.</p>
        </section>

        <div className="flex flex-wrap items-center gap-3 border-t pt-6">
          <button type="button" disabled aria-describedby="start-why" className="rounded bg-emerald-700 px-5 py-2.5 font-medium text-white disabled:cursor-not-allowed disabled:opacity-50">Start training</button>
          <span id="start-why" className="text-sm text-neutral-600">Disabled until the backend supports this job.</span>
        </div>
      </form>

      <section id="missing" className="space-y-3 rounded border bg-white p-5">
        <h2 className="text-xl font-semibold">What&apos;s missing before training can start</h2>
        <ul className="list-disc space-y-2 pl-6 text-sm">{MISSING.map((m) => <li key={m}>{m}</li>)}</ul>
        <p className="text-sm">The exact backend changes are written up in the <Link className="underline" href="/docs/train-contract">Train AI model contract</Link>.</p>
      </section>

      <section className="space-y-2">
        <h2 className="text-xl font-semibold">What you can train today</h2>
        <p>A real, small <span className="font-mono">linear_regression_v1</span> training job runs on the backend now. Follow the <Link className="underline" href="/docs/quickstart">developer quickstart</Link> to submit it, then see the result and download the model on the <Link className="underline" href="/jobs">Jobs</Link> page.</p>
        <p className="text-sm text-neutral-600">Setting up the ThinkPad and the Mac? Start with the <Link className="underline" href="/docs/setup">Setup &amp; Git guide</Link>.</p>
      </section>
    </article>
  );
}
