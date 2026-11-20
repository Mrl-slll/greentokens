#!/usr/bin/env bash
# GreenTokens provider check (Linux / macOS). Read-only: installs and changes nothing.
# Run:  bash provider_check.sh <address you were given>
# Then send the printed block back to the GreenTokens operator.
SERVER="${1:-}"

echo "== GreenTokens provider check ($(uname -s)) =="
if [ -f /etc/os-release ]; then . /etc/os-release; echo "OS: $PRETTY_NAME ($(uname -m))"; else echo "OS: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"; fi
if command -v nproc >/dev/null; then echo "CPU threads: $(nproc)"; else echo "CPU threads: $(sysctl -n hw.ncpu 2>/dev/null)"; fi
if [ -r /proc/meminfo ]; then awk '/MemTotal/ {printf "RAM: %.1f GB\n", $2/1048576}' /proc/meminfo; else echo "RAM: $(( $(sysctl -n hw.memsize 2>/dev/null) / 1073741824 )) GB"; fi

if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | sed 's/^/GPU: /'
  nvidia-smi | grep -o "CUDA Version: [0-9.]*" | head -1 | sed 's/CUDA Version:/CUDA supported by driver:/'
else
  echo "GPU: no NVIDIA driver found (nvidia-smi missing)"
fi

if [ "$(uname -s)" = "Darwin" ]; then echo "Network addresses: $(ipconfig getifaddr en0 2>/dev/null) $(ipconfig getifaddr en1 2>/dev/null)"
elif hostname -I >/dev/null 2>&1; then echo "Network addresses: $(hostname -I)"
elif command -v ip >/dev/null; then echo "Network addresses: $(ip -4 -o addr show scope global | awk '{print $4}' | tr '\n' ' ')"
else echo "Network addresses: unknown"; fi
if command -v tailscale >/dev/null; then echo "Tailscale: installed"; else echo "Tailscale: not installed"; fi
echo "Disk free: $(df -h . | awk 'NR==2 {print $4}')"

if [ -n "$SERVER" ]; then
  if command -v nc >/dev/null && nc -z -w 3 "$SERVER" 6379 2>/dev/null; then ok=YES
  elif (exec 3<>"/dev/tcp/$SERVER/6379") 2>/dev/null; then ok=YES
  else ok=NO; fi
  echo "Can reach GreenTokens server $SERVER:6379 -> $ok"
fi
echo "== end =="
