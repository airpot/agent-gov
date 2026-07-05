#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const PACKAGE_ROOT = path.resolve(__dirname, "../..");
const PACKAGE_JSON = path.join(PACKAGE_ROOT, "package.json");
const SKILLS_SOURCE = path.join(PACKAGE_ROOT, ".codex", "skills");
const INIT_SCRIPT = path.join(SKILLS_SOURCE, "agent-gov", "scripts", "init_agent_project.py");
const RUNTIME_SKILLS = [
  "agent-gov",
];
const IGNORE_DIRS = new Set(["__pycache__", ".git", ".skvm"]);
const IGNORE_SUFFIXES = new Set([".pyc", ".pyo", ".log"]);

function readPackage() {
  return JSON.parse(fs.readFileSync(PACKAGE_JSON, "utf8"));
}

function printHelp() {
  const version = readPackage().version;
  console.log(`agent-gov ${version}

Usage:
  agent-gov [root] [initializer options]
  agent-gov init [root] [initializer options]
  agent-gov install-skill [root] [--force] [--dry-run] [--global]
  agent-gov doctor [root]

Examples:
  npx @airpot/agent-gov@latest
  npx @airpot/agent-gov@latest --tech-stack python,typescript --layout service
  npx @airpot/agent-gov@latest --governance-profile full
  npx @airpot/agent-gov@latest init /path/to/repo --remote-kind ssh

Default behavior:
  Installs the bundled agent-gov project skill into <root>/.codex/skills, then runs the
  agent-gov initializer for <root>. Existing skill files are preserved unless
  --force or --force-skill is provided. When --governance-profile is omitted,
  blank projects default to full and existing projects default to standard.
  install-skill also defaults to project scope. Use --global only when the user
  explicitly wants to mutate the user-level Codex skill directory.

Local npm-only options:
  --skip-skill-install   Run the Python initializer without copying the bundled skill.
  --force-skill          Overwrite existing bundled skill files.
  --global               Install bundled skills into the user-level Codex skill directory.
  --help, -h             Show this help.
  --version, -v          Show the package version.

Initializer options are passed through to init_agent_project.py.`);
}

function printVersion() {
  console.log(readPackage().version);
}

function commandExists(command, args = ["--version"]) {
  const result = spawnSync(command, args, { stdio: "ignore" });
  return result.status === 0;
}

function findPython() {
  if (process.env.AGENT_GOV_PYTHON) {
    return { command: process.env.AGENT_GOV_PYTHON, args: [] };
  }
  if (commandExists("python3")) {
    return { command: "python3", args: [] };
  }
  if (commandExists("python")) {
    return { command: "python", args: [] };
  }
  if (commandExists("py", ["-3", "--version"])) {
    return { command: "py", args: ["-3"] };
  }
  return null;
}

function shouldSkip(sourcePath) {
  const parts = sourcePath.split(path.sep);
  if (parts.some((part) => IGNORE_DIRS.has(part))) {
    return true;
  }
  return IGNORE_SUFFIXES.has(path.extname(sourcePath));
}

function filesEqual(left, right) {
  try {
    if (!fs.existsSync(left) || !fs.existsSync(right)) {
      return false;
    }
    const leftStat = fs.statSync(left);
    const rightStat = fs.statSync(right);
    if (!leftStat.isFile() || !rightStat.isFile() || leftStat.size !== rightStat.size) {
      return false;
    }
    return fs.readFileSync(left).equals(fs.readFileSync(right));
  } catch {
    return false;
  }
}

function copyTree(source, dest, options) {
  const result = { copied: 0, skipped: 0, unchanged: 0, conflicts: 0 };
  if (!fs.existsSync(source)) {
    return result;
  }
  for (const entry of fs.readdirSync(source, { withFileTypes: true })) {
    const sourcePath = path.join(source, entry.name);
    const destPath = path.join(dest, entry.name);
    if (shouldSkip(sourcePath)) {
      continue;
    }
    if (entry.isDirectory()) {
      const nested = copyTree(sourcePath, destPath, options);
      result.copied += nested.copied;
      result.skipped += nested.skipped;
      result.unchanged += nested.unchanged;
      result.conflicts += nested.conflicts;
      continue;
    }
    if (!entry.isFile()) {
      continue;
    }
    if (fs.existsSync(destPath) && !options.force) {
      if (filesEqual(sourcePath, destPath)) {
        result.unchanged += 1;
      } else {
        result.skipped += 1;
        result.conflicts += 1;
      }
      continue;
    }
    result.copied += 1;
    if (!options.dryRun) {
      fs.mkdirSync(path.dirname(destPath), { recursive: true });
      fs.copyFileSync(sourcePath, destPath);
      fs.chmodSync(destPath, fs.statSync(sourcePath).mode & 0o777);
    }
  }
  return result;
}

function installSkills(targetRoot, options = {}) {
  const scope = options.global ? "global" : "project";
  const skillDest = options.global ? globalSkillDir() : path.join(targetRoot, ".codex", "skills");
  let copied = 0;
  let skipped = 0;
  let unchanged = 0;
  let conflicts = 0;
  for (const skill of RUNTIME_SKILLS) {
    const source = path.join(SKILLS_SOURCE, skill);
    const dest = path.join(skillDest, skill);
    const result = copyTree(source, dest, options);
    copied += result.copied;
    skipped += result.skipped;
    unchanged += result.unchanged;
    conflicts += result.conflicts;
  }
  console.log(`skill source: ${SKILLS_SOURCE}`);
  console.log(`skill scope: ${scope}`);
  console.log(`skill dest: ${skillDest}`);
  console.log(`skill files ${options.dryRun ? "would copy" : "copied"}: ${copied}`);
  console.log(`skill files unchanged: ${unchanged}`);
  console.log(`skill file conflicts preserved: ${conflicts}`);
  if (conflicts > 0 && !options.force) {
    console.log("existing different skill files were preserved; rerun with --force-skill or --force only after reviewing the local changes");
  }
}

function homeDir() {
  return process.env.HOME || process.env.USERPROFILE || "";
}

function globalSkillDir() {
  if (process.env.CODEX_HOME) {
    return path.resolve(process.env.CODEX_HOME, "skills");
  }
  const home = homeDir();
  if (!home) {
    throw new Error("cannot resolve global skill directory: HOME, USERPROFILE, or CODEX_HOME is required");
  }
  return path.resolve(home, ".codex", "skills");
}

function firstPositional(args) {
  if (args.length > 0 && !args[0].startsWith("-")) {
    return args[0];
  }
  return ".";
}

function parseInstallArgs(args) {
  const result = {
    target: ".",
    force: false,
    dryRun: false,
    global: false,
  };
  let targetSet = false;
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--force" || arg === "--force-skill") {
      result.force = true;
    } else if (arg === "--dry-run") {
      result.dryRun = true;
    } else if (arg === "--global") {
      result.global = true;
    } else if (arg === "--target") {
      i += 1;
      if (!args[i]) {
        throw new Error("--target requires a path");
      }
      result.target = args[i];
      targetSet = true;
    } else if (arg.startsWith("--target=")) {
      result.target = arg.slice("--target=".length);
      targetSet = true;
    } else if (arg === "--help" || arg === "-h") {
      printHelp();
      process.exit(0);
    } else if (!arg.startsWith("-") && !targetSet) {
      result.target = arg;
      targetSet = true;
    } else {
      throw new Error(`unknown install-skill option: ${arg}`);
    }
  }
  return result;
}

function ensureTargetRoot(targetRoot, args, dryRun) {
  if (fs.existsSync(targetRoot)) {
    return;
  }
  if (args.includes("--create-root")) {
    if (!dryRun) {
      fs.mkdirSync(targetRoot, { recursive: true });
    }
    return;
  }
  throw new Error(`target root does not exist: ${targetRoot}`);
}

function splitInitArgs(args) {
  const passthrough = [];
  let skipSkillInstall = false;
  let forceSkill = false;
  for (const arg of args) {
    if (arg === "--skip-skill-install") {
      skipSkillInstall = true;
    } else if (arg === "--force-skill") {
      forceSkill = true;
    } else {
      passthrough.push(arg);
    }
  }
  return { passthrough, skipSkillInstall, forceSkill };
}

function runInitializer(args) {
  if (!fs.existsSync(INIT_SCRIPT)) {
    throw new Error(`initializer missing from npm package: ${INIT_SCRIPT}`);
  }
  const python = findPython();
  if (!python) {
    throw new Error("Python 3 is required. Set AGENT_GOV_PYTHON or install python3.");
  }
  const result = spawnSync(
    python.command,
    [...python.args, INIT_SCRIPT, ...args],
    { cwd: process.cwd(), stdio: "inherit" },
  );
  if (result.error) {
    throw result.error;
  }
  return result.status ?? 1;
}

function init(args) {
  const { passthrough, skipSkillInstall, forceSkill } = splitInitArgs(args);
  const rootArg = firstPositional(passthrough);
  const targetRoot = path.resolve(process.cwd(), rootArg);
  const dryRun = passthrough.includes("--dry-run");
  const force = forceSkill || passthrough.includes("--force");
  ensureTargetRoot(targetRoot, passthrough, dryRun);
  if (!skipSkillInstall) {
    installSkills(targetRoot, { force, dryRun });
  }
  const initializerArgs = passthrough.length > 0 && !passthrough[0].startsWith("-")
    ? passthrough
    : [targetRoot, ...passthrough];
  return runInitializer(initializerArgs);
}

function installSkill(args) {
  const options = parseInstallArgs(args);
  const targetRoot = path.resolve(process.cwd(), options.target);
  if (!options.global) {
    ensureTargetRoot(targetRoot, [], options.dryRun);
  }
  installSkills(targetRoot, options);
  return 0;
}

function doctor(args) {
  const targetRoot = path.resolve(process.cwd(), firstPositional(args));
  const python = findPython();
  const checks = [
    ["package", fs.existsSync(PACKAGE_JSON), PACKAGE_JSON],
    ["initializer", fs.existsSync(INIT_SCRIPT), INIT_SCRIPT],
    ["bundled agent-gov skill", fs.existsSync(path.join(SKILLS_SOURCE, "agent-gov", "SKILL.md")), path.join(SKILLS_SOURCE, "agent-gov")],
    ["python", Boolean(python), python ? `${python.command} ${python.args.join(" ")}`.trim() : "missing"],
    ["target root", fs.existsSync(targetRoot), targetRoot],
    ["target agent-gov skill", fs.existsSync(path.join(targetRoot, ".codex", "skills", "agent-gov", "SKILL.md")), path.join(targetRoot, ".codex", "skills", "agent-gov")],
  ];
  let failed = false;
  for (const [name, ok, detail] of checks) {
    console.log(`${ok ? "ok" : "missing"} - ${name}: ${detail}`);
    if (!ok) {
      failed = true;
    }
  }
  return failed ? 1 : 0;
}

function main(argv) {
  const commands = new Set(["init", "install-skill", "doctor", "help", "version"]);
  let command = "init";
  const args = [...argv];
  if (args.length > 0 && commands.has(args[0])) {
    command = args.shift();
  } else if (args[0] === "--help" || args[0] === "-h") {
    command = "help";
    args.shift();
  } else if (args[0] === "--version" || args[0] === "-v") {
    command = "version";
    args.shift();
  }

  if (command === "help") {
    printHelp();
    return 0;
  }
  if (command === "version") {
    printVersion();
    return 0;
  }
  if (command === "install-skill") {
    return installSkill(args);
  }
  if (command === "doctor") {
    return doctor(args);
  }
  return init(args);
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  console.error(`agent-gov: ${error.message}`);
  process.exitCode = 1;
}
