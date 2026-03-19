#!/usr/bin/env node

/**
 * postinstall.js — runs after `npm install claudezh`
 *
 * 1. Verify Python 3.10+ is available
 * 2. Install Python dependencies from the bundled source
 */

"use strict";

const { execSync } = require("child_process");
const path = require("path");

function run(cmd) {
  try {
    return execSync(cmd, { encoding: "utf8", stdio: ["pipe", "pipe", "pipe"] }).trim();
  } catch {
    return null;
  }
}

function parsePythonVersion(versionStr) {
  if (!versionStr) return null;
  const m = versionStr.match(/Python\s+(\d+)\.(\d+)/);
  if (!m) return null;
  return [parseInt(m[1], 10), parseInt(m[2], 10)];
}

function findPython() {
  for (const cmd of ["python3", "python"]) {
    const ver = run(`${cmd} --version`);
    const parsed = parsePythonVersion(ver);
    if (parsed && parsed[0] === 3 && parsed[1] >= 10) {
      return cmd;
    }
  }
  return null;
}

function main() {
  console.log("");
  console.log("╔══════════════════════════════════════════════╗");
  console.log("║       claudezh — 全中文 AI 编程助手          ║");
  console.log("║       Chinese AI Coding Assistant            ║");
  console.log("╚══════════════════════════════════════════════╝");
  console.log("");

  // Step 1: Check Python
  const pythonCmd = findPython();
  if (!pythonCmd) {
    console.warn(
      "\x1b[33m[claudezh] 警告: 未检测到 Python 3.10+\x1b[0m\n" +
        "claudezh 需要 Python 3.10 或更高版本。\n" +
        "请安装后重新运行: https://www.python.org/downloads/\n" +
        "\n" +
        "[claudezh] Warning: Python 3.10+ not found.\n" +
        "Please install Python 3.10+ and re-run: npm rebuild claudezh\n"
    );
    // Don't exit with error — npm postinstall failure blocks the whole install
    return;
  }

  const pyVer = run(`${pythonCmd} --version`);
  console.log(`[claudezh] Python: ${pyVer}`);

  // Step 2: Install Python dependencies from bundled source
  const pkgDir = path.resolve(__dirname, "..");
  console.log("[claudezh] 正在安装 Python 依赖 (Installing Python dependencies)...");

  // Try with --break-system-packages first (PEP 668 on Debian/Ubuntu)
  let installed = false;
  const pipCmds = [
    `${pythonCmd} -m pip install -e "${pkgDir}" --break-system-packages -q`,
    `${pythonCmd} -m pip install -e "${pkgDir}" -q`,
  ];
  for (const cmd of pipCmds) {
    if (run(cmd) !== null) {
      installed = true;
      break;
    }
  }

  if (installed) {
    console.log("");
    console.log("\x1b[32m[claudezh] 安装完成！(Installation complete!)\x1b[0m");
    console.log("");
    console.log("  使用方法 (Usage):");
    console.log("    claudezh            启动交互式助手");
    console.log("    claudezh --help     查看帮助");
    console.log("");
    console.log("  首次使用请设置 API Key:");
    console.log("    export ANTHROPIC_API_KEY=your-key-here");
    console.log("");
  } else {
    console.warn(
      "\x1b[33m[claudezh] 警告: Python 依赖自动安装失败\x1b[0m\n" +
        "请手动执行 (Please run manually):\n" +
        `  ${pythonCmd} -m pip install -e "${pkgDir}"\n`
    );
  }
}

main();
