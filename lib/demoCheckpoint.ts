import { readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

export const DEMO_RUNS_DIR = path.join("examples", "bert_tiny_cpu");

export interface DemoMetrics {
  model: string;
  mode: string;
  versions: Record<string, string>;
  settings: { examples: number; epochs: number; threads: number; max_length: number };
  learning_rate: number;
  epoch_train_losses: number[];
  validation_accuracy: number;
  training_loop_seconds: number;
  checkpoint_reload_verified: boolean;
  training_subset_sha256: string;
  prediction: { sentence: string; label: string; probability: number };
}

// Same rule as scripts/predict_cpu.py: newest bert-tiny-run-* with a verified reload.
export async function latestDemoRun(root = process.cwd()): Promise<{ name: string; metrics: DemoMetrics } | null> {
  const runsDir = path.join(root, DEMO_RUNS_DIR);
  let names: string[];
  try { names = await readdir(runsDir); } catch { return null; }
  for (const name of names.filter(n => n.startsWith("bert-tiny-run-")).sort().reverse()) {
    try {
      const metrics = JSON.parse(await readFile(path.join(runsDir, name, "metrics.json"), "utf8"));
      if (metrics.checkpoint_reload_verified !== true) continue;
      if (!(await stat(path.join(runsDir, name, "model.safetensors"))).isFile()) continue;
      return { name, metrics };
    } catch { continue; }
  }
  return null;
}
