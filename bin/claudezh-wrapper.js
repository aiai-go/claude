#!/usr/bin/env node

/**
 * claudezh — npm wrapper for the Python CLI
 *
 * Flow:
 *   1. Find a usable Python >= 3.10
 *   2. Ensure the aicodezh package is importable
 *   3. Spawn `python3 -m aicodezh.cli` with inherited stdio
 */

"use strict";

const { execSync, spawn } = require("child_process");
const path = require("path");

// ── helpers ──────────────────────────────────────────────────────────────

/** Run a command silently and return trimmed stdout, or null on failure. */
function run(cmd) {
  try {
    return execSync(cmd, { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }).trim();
  } catch {
    return null;
  }
}

/** Parse "Python 3.x.y" and return [major, minor] or null. */
function parsePythonVersion(versionStr) {
  if (!versionStr) return null;
  const m = versionStr.match(/Python\s+(\d+)\.(\d+)/);
  if (!m) return null;
  return [parseInt(m[1], 10), parseInt(m[2], 10)];
}

/** Find a Python >= 3.10 binary. Returns the command string or exits. */
function findPython() {
  for (const cmd of ["python3", "python"]) {
    const ver = run(`${cmd} --version`);
    const parsed = parsePythonVersion(ver);
    if (parsed && parsed[0] === 3 && parsed[1] >= 10) {
      return cmd;
    }
  }
  console.error(
    "\x1b[31m[claudezh] 错误: 未找到 Python 3.10+\x1b[0m\n" +
      "请先安装 Python 3.10 或更高版本: https://www.python.org/downloads/"
  );
  process.exit(1);
}

/** Check whether the aicodezh package is importable. */
function isPackageInstalled(pythonCmd) {
  return run(`${pythonCmd} -c "import aicodezh"`) !== null;
}

/** Install the bundled Python package from the npm package directory. */
function installBundledPackage(pythonCmd) {
  const pkgDir = path.resolve(__dirname, "..");
  console.log("[claudezh] 正在安装 Python 依赖...");

  // Try with --break-system-packages first (PEP 668), fall back without
  const pipCmds = [
    `${pythonCmd} -m pip install -e "${pkgDir}" --break-system-packages -q`,
    `${pythonCmd} -m pip install -e "${pkgDir}" -q`,
  ];
  for (const cmd of pipCmds) {
    const result = run(cmd);
    if (result !== null) {
      console.log("[claudezh] Python 依赖安装完成 ✓");
      return true;
    }
  }
  console.error(
    "\x1b[31m[claudezh] 错误: 无法安装 Python 依赖\x1b[0m\n" +
      "请手动执行: pip install -e " + pkgDir
  );
  return false;
}

// ── main ─────────────────────────────────────────────────────────────────

function main() {
  const pythonCmd = findPython();

  // Auto-install if the package is not yet importable
  if (!isPackageInstalled(pythonCmd)) {
    if (!installBundledPackage(pythonCmd)) {
      process.exit(1);
    }
  }

  // Forward all CLI arguments to the Python entry point
  const args = ["-m", "aicodezh.cli", ...process.argv.slice(2)];
  const child = spawn(pythonCmd, args, {
    stdio: "inherit",
    env: process.env,
  });

  // Relay signals
  for (const sig of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    process.on(sig, () => child.kill(sig));
  }

  child.on("exit", (code, signal) => {
    if (signal) {
      process.kill(process.pid, signal);
    } else {
      process.exit(code ?? 1);
    }
  });

  child.on("error", (err) => {
    console.error(`[claudezh] 启动失败: ${err.message}`);
    process.exit(1);
  });
}

main();
