export default function Pipelines() {
  return <article className="space-y-8 leading-7"><header><h1 className="text-3xl font-semibold">Pipelines & data</h1><p>Select an approved workload. This MVP does not execute uploaded Python scripts.</p></header>
    <table className="w-full border-collapse text-left text-sm"><thead><tr className="border-b"><th className="p-2">Pipeline</th><th className="p-2">Input</th><th className="p-2">Output</th></tr></thead><tbody>
      <tr className="border-b"><td className="p-2 font-mono">sum_numbers_v1</td><td className="p-2">1–1,000 integers in a values array</td><td className="p-2">Sum</td></tr>
      <tr className="border-b"><td className="p-2 font-mono">linear_regression_v1</td><td className="p-2">2–1,000 paired x/y samples; x must vary</td><td className="p-2">Slope, intercept, training error, sample count</td></tr>
    </tbody></table>
    <section className="space-y-3"><h2 className="text-xl font-semibold">Where your data goes</h2>
      <ol className="list-decimal space-y-3 pl-6"><li><strong>Your project:</strong> a JSON dataset and TOML pipeline. Dataset paths are relative to the pipeline file.</li>
        <li><strong>Client → API:</strong> submit sends the JSON to the backend. Explain sends nothing.</li>
        <li><strong>API → MySQL:</strong> validated inline inputs, requested resources, ownership, and job state are stored in the job record.</li>
        <li><strong>Ray worker:</strong> reads the input and executes the selected CPU pipeline.</li>
        <li><strong>Worker → S3:</strong> results and collected logs become artifacts. MySQL stores their IDs, checksums, sizes, and expiry.</li>
        <li><strong>API → you:</strong> ownership and integrity checks protect reads. Download results using the CLI or job page.</li></ol></section>
    <section className="space-y-3"><h2 className="text-xl font-semibold">Storage access</h2><p>Use the API through the SDK. You do not need credentials for GreenTokens&apos; internal MySQL database. The supported dataset source is a local JSON file; external database and cloud-bucket connectors are not implemented.</p>
      <p>The SDK also supports <code>client.upload(data)</code>, followed by submission with its <code>input_artifact_id</code>. That stores the dataset in S3 and a reference in the job record.</p></section>
    <section className="space-y-3"><h2 className="text-xl font-semibold">Current limits</h2><ul className="list-disc space-y-2 pl-6"><li>Local development only. Alice and bob are test identities, not authenticated accounts.</li>
      <li>One CPU worker fits one feature. GPU, neural-network, and distributed model training are not implemented.</li><li>Datasets and artifacts are limited to 64 KiB. Training values must be finite and within ±1,000,000.</li>
      <li>Artifact access expires after 24 hours; physical cleanup is not guaranteed. Inline inputs remain in job records.</li><li>Logs are collected after execution, not streamed live.</li><li>Custom scripts, remote authentication, GPU provisioning, and external storage connections are later milestones.</li></ul></section>
  </article>;
}
