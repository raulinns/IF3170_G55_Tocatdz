import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";
import { fileURLToPath } from "node:url";

const frontendDirectory = fileURLToPath(new URL("..", import.meta.url));
const projectDirectory = fileURLToPath(new URL("../..", import.meta.url));
const isWindows = process.platform === "win32";
const children = [];
let closing = false;

function start(command, args, cwd) {
  const child = spawn(command, args, {
    cwd,
    stdio: "inherit",
    shell: isWindows,
    detached: !isWindows,
  });
  children.push(child);
  child.on("error", (error) => {
    console.error(`Gagal menjalankan ${command}: ${error.message}`);
    shutdown(1);
  });
  child.on("exit", (code, signal) => {
    if (!closing) {
      console.error(`${command} berhenti (${signal ?? code ?? 0}).`);
      shutdown(code ?? 1);
    }
  });
  return child;
}

function stop(child) {
  if (!child.pid || child.killed) return;
  try {
    if (isWindows) child.kill("SIGTERM");
    else process.kill(-child.pid, "SIGTERM");
  } catch {
    // Proses mungkin sudah selesai lebih dahulu.
  }
}

function shutdown(exitCode = 0) {
  if (closing) return;
  closing = true;
  children.forEach(stop);
  setTimeout(() => process.exit(exitCode), 150).unref();
}

async function waitForBackend() {
  for (let attempt = 0; attempt < 120 && !closing; attempt += 1) {
    try {
      const response = await fetch("http://127.0.0.1:8000/api/problems/example");
      if (response.ok) return;
    } catch {
      // FastAPI masih dalam proses startup.
    }
    await delay(500);
  }
  throw new Error("FastAPI tidak siap pada http://127.0.0.1:8000.");
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

start("uv", ["run", "--no-cache", "uvicorn", "webapi.main:app", "--reload", "--host", "127.0.0.1", "--port", "8000"], projectDirectory);

try {
  await waitForBackend();
  if (!closing) start(isWindows ? "npm.cmd" : "npm", ["run", "dev:client"], frontendDirectory);
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error));
  shutdown(1);
}
