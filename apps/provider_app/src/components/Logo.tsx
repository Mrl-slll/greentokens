export function Logo({ size = 36 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 1024 1024" aria-hidden>
      <rect width="1024" height="1024" rx="224" fill="#047857" />
      <path d="M512 196c-174 0-316 142-316 316s142 316 316 316 316-142 316-316H520" fill="none" stroke="#fff" strokeWidth="96" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M640 512c0-71-57-128-128-128" fill="none" stroke="#a7f3d0" strokeWidth="72" strokeLinecap="round" />
    </svg>
  );
}
