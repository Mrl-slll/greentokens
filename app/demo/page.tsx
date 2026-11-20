import { ModelDemo } from "@/components/ModelDemo";
import { latestDemoRun } from "@/lib/demoCheckpoint";

export const dynamic = "force-dynamic";
export default async function Demo() {
  const run = await latestDemoRun();
  if (!run) return <main className="p-10">Training evidence is unavailable on this computer. No results are being simulated.</main>;
  const { metrics } = run;
  return <main className="min-h-screen bg-slate-50 px-5 py-10 text-slate-900 sm:px-10">
    <div className="mx-auto max-w-5xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 pb-6"><div><p className="text-sm font-semibold tracking-widest text-emerald-700">GREENTOKENS / WORKING PROTOTYPE</p><h1 className="mt-3 text-3xl font-semibold sm:text-4xl">Useful AI training on everyday CPUs.</h1><p className="mt-3 max-w-2xl text-slate-600">Today: a real model trained and reloaded on one laptop. Next: coordinate training across independent computers.</p></div><span className="rounded-full border border-emerald-300 bg-emerald-50 px-3 py-1 text-sm text-emerald-900">Single-computer result verified</span></header>
      <section aria-label="Measured training results" className="grid gap-4 sm:grid-cols-4">
        {[["Validation accuracy", `${(metrics.validation_accuracy * 100).toFixed(1)}%`], ["Training time", `${metrics.training_loop_seconds.toFixed(1)}s`], ["Training samples", String(metrics.settings.examples)], ["CPU threads", String(metrics.settings.threads)]].map(([label, value]) => <div key={label} className="rounded-xl border border-slate-200 bg-white p-5"><p className="text-sm text-slate-500">{label}</p><p className="mt-2 text-3xl font-semibold">{value}</p></div>)}
      </section>
      <p className="text-sm text-slate-600">BERT-Tiny · SST-2 English sentiment classification · {metrics.settings.epochs} epochs · learning rate {metrics.learning_rate} · 872 held-out validation examples. Training time excludes installation, imports, and data preparation. This is an early baseline.</p>
      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6"><h2 className="mb-4 text-xl font-semibold">1. Try the trained model</h2><ModelDemo /></div>
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6"><h2 className="text-xl font-semibold">2. Inspect the training evidence</h2><p className="text-sm text-slate-600">Read from the completed run&apos;s metrics file on this computer.</p>
          <dl className="grid grid-cols-2 gap-3 text-sm"><dt>Checkpoint</dt><dd className="break-all font-mono text-xs">{run.name}</dd><dt>Execution</dt><dd>Single computer / CPU</dd><dt>Checkpoint reload</dt><dd>{metrics.checkpoint_reload_verified ? "Passed" : "Not verified"}</dd><dt>Epoch loss</dt><dd>{metrics.epoch_train_losses.map((n: number) => n.toFixed(3)).join(" → ")}</dd><dt>Recorded sample</dt><dd>{metrics.prediction.label}</dd></dl>
          <p className="rounded bg-slate-50 p-3 text-sm">“{metrics.prediction.sentence}”<br />Recorded model score: {(metrics.prediction.probability * 100).toFixed(1)}%</p>
          <a className="inline-block text-sm font-medium underline" download="greentokens-training-evidence.json" href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify({checkpoint: run.name, model: metrics.model, mode: metrics.mode, versions: metrics.versions, examples: metrics.settings.examples, epochs: metrics.settings.epochs, learning_rate: metrics.learning_rate, max_length: metrics.settings.max_length, threads: metrics.settings.threads, validation_examples: 872, validation_accuracy: metrics.validation_accuracy, training_loop_seconds: metrics.training_loop_seconds, epoch_train_losses: metrics.epoch_train_losses, checkpoint_reload_verified: metrics.checkpoint_reload_verified, training_subset_sha256: metrics.training_subset_sha256}, null, 2))}`}>Download measured results</a>
        </div>
      </section>
      <section className="space-y-4 rounded-xl border border-amber-300 bg-amber-50 p-6"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-semibold">3. How four-computer training will work</h2><span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-amber-900">PLANNED ARCHITECTURE · NOT A LIVE CLUSTER</span></div>
        <div className="grid gap-3 sm:grid-cols-4">{["This laptop", "Computer 2", "Computer 3", "Computer 4"].map((name, i) => <div key={name} className="rounded-lg border border-amber-200 bg-white p-4"><p className="font-semibold">{name}</p><p className="mt-2 text-sm">{i === 0 ? "Completed the recorded CPU run" : "Not connected"}</p></div>)}</div>
        <p className="text-sm">Planned flow: Ray assigns one worker to each machine → workers process different data shards → PyTorch synchronizes gradients → one shared model checkpoint.</p>
        <p className="text-sm font-medium">Multi-computer training and any speedup have not been demonstrated. Next proof: four distinct hosts, one synchronized training run, and a reloadable checkpoint.</p>
      </section>
      <footer className="text-sm text-slate-500">The BERT demo runs directly from its saved checkpoint. It is separate from the existing GreenTokens Ray job API. No GPU, cloud account, or connected provider machines were used for this result.</footer>
    </div>
  </main>;
}
