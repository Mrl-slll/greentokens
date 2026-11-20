/** Tiny line chart of recent values (plain SVG, no chart library). */
export function Sparkline({ values, max = 100, label }: { values: number[]; max?: number; label: string }) {
  const width = 240;
  const height = 40;
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const points = values
    .map((v, i) => `${(i * step).toFixed(1)},${(height - (Math.min(Math.max(v, 0), max) / max) * height).toFixed(1)}`)
    .join(" ");
  return (
    <svg role="img" aria-label={label} viewBox={`0 0 ${width} ${height}`} className="mt-2 h-10 w-full text-emerald-600" preserveAspectRatio="none">
      <line x1="0" y1={height - 0.5} x2={width} y2={height - 0.5} stroke="currentColor" strokeOpacity="0.2" />
      {values.length > 1 && <polyline points={points} fill="none" stroke="currentColor" strokeWidth="2" vectorEffect="non-scaling-stroke" />}
    </svg>
  );
}
