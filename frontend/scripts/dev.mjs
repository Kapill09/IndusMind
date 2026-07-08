import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const isWindows = process.platform === "win32";

function findPythonExecutable() {
  const candidates = [
    process.env.PYTHON,
    process.env.VIRTUAL_ENV && path.join(process.env.VIRTUAL_ENV, isWindows ? "Scripts/python.exe" : "bin/python"),
    isWindows ? path.join(repoRoot, "venv", "Scripts", "python.exe") : path.join(repoRoot, "venv", "bin", "python"),
    isWindows ? path.join(repoRoot, ".venv", "Scripts", "python.exe") : path.join(repoRoot, ".venv", "bin", "python"),
    "python",
    "python3",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (candidate.includes(path.sep) && existsSync(candidate)) {
      return candidate;
    }

    if (!candidate.includes(path.sep)) {
      return candidate;
    }
  }

  return "python";
}

function runCommand(command, args, options = {}) {
  const child = spawn(command, args, {
    stdio: "inherit",
    shell: false,
    ...options,
  });

  child.on("exit", (code) => {
    if (code && code !== 0) {
      process.exit(code);
    }
  });

  return child;
}

async function waitForBackend(url, timeoutMs = 60000) {
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(2000) });
      if (response.ok) {
        return;
      }
    } catch {
      // Keep retrying while the backend is still coming up.
    }

    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Backend did not become ready at ${url}`);
}

async function main() {
  const pythonExecutable = findPythonExecutable();
  let backend = null;

  try {
    await fetch("http://127.0.0.1:8000/", { signal: AbortSignal.timeout(2000) });
    console.log("Backend API is already running.");
  } catch {
    console.log("Starting backend API...");
    backend = runCommand(pythonExecutable, ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"], {
      cwd: repoRoot,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },
    });
    await waitForBackend("http://127.0.0.1:8000/");
  }

  console.log("Backend is ready. Starting frontend dev server...");
  const frontend = runCommand(isWindows ? "npm.cmd" : "npm", ["run", "dev:frontend"], {
    cwd: frontendRoot,
  });

  try {

    const shutdown = () => {
      if (backend) {
        backend.kill("SIGTERM");
      }
      frontend.kill("SIGTERM");
      process.exit(0);
    };

    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    if (backend) {
      backend.kill("SIGTERM");
    }
    frontend.kill("SIGTERM");
    process.exit(1);
  }
}

main();
