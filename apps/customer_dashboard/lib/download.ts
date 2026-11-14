/** Filename built only from the artifact kind and a UUID-shaped ID: never from server-supplied names. */
export const safeFilename = (kind: string, id: string) => {
  const k = kind.replace(/[^a-z]/gi, "") || "file", i = id.replace(/[^0-9a-f-]/gi, "").slice(0, 36) || "unknown";
  return `greentokens-${k}-${i}.${k === "log" ? "txt" : "json"}`;
};
export function saveText(text: string, name: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000); // release the temporary object URL
}
