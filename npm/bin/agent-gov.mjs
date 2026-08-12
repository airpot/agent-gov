#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
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
const IGNORE_DIRS = new Set(["__pycache__", ".git", ".skvm", "node_modules", "dist", "build", "target"]);
const IGNORE_NAMES = new Set([".DS_Store", ".agent-gov-install.json"]);
const IGNORE_SUFFIXES = new Set([".pyc", ".pyo", ".log"]);
const INSTALL_MANIFEST = ".agent-gov-install.json";
const INIT_VALUE_OPTIONS = new Set([
  "--project-name",
  "--tech-stack",
  "--layout",
  "--governance-profile",
  "--dir",
  "--client-surface",
  "--remote-kind",
  "--spec-mode",
  "--install-openspec",
  "--openspec-package-manager",
  "--openspec-tools",
  "--architecture-intake",
]);

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
  agent-gov readiness [root]

Examples:
  npx @airpot/agent-gov@latest
  npx @airpot/agent-gov@latest --tech-stack python,typescript --layout service
  npx @airpot/agent-gov@latest --governance-profile full
  npx @airpot/agent-gov@latest init /path/to/repo --remote-kind ssh

Default behavior:
  Installs the bundled agent-gov project skill into <root>/.codex/skills, then runs the
  agent-gov initializer for <root>. A different, unmanifested, or drifted existing
  skill fails closed instead of being partially merged; use --force or --force-skill
  only after reviewing the replacement. When --governance-profile is omitted,
  blank projects default to full and existing projects default to standard.
  install-skill also defaults to project scope. Use --global only when the user
  explicitly wants to mutate the user-level Codex skill directory.
  Python 3.10 or newer is required for initialization and generated tools.

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

function pythonProbe(command, args = []) {
  const result = spawnSync(
    command,
    [
      ...args,
      "-c",
      "import sys; assert sys.version_info >= (3, 10); print('agent-gov-python3')",
    ],
    { encoding: "utf8" },
  );
  return result.status === 0 && result.stdout.trim() === "agent-gov-python3";
}

function findPython() {
  if (process.env.AGENT_GOV_PYTHON) {
    return pythonProbe(process.env.AGENT_GOV_PYTHON)
      ? { command: process.env.AGENT_GOV_PYTHON, args: [] }
      : null;
  }
  if (pythonProbe("python3")) {
    return { command: "python3", args: [] };
  }
  if (pythonProbe("python")) {
    return { command: "python", args: [] };
  }
  if (pythonProbe("py", ["-3"])) {
    return { command: "py", args: ["-3"] };
  }
  return null;
}

function requirePython() {
  const python = findPython();
  if (!python) {
    throw new Error("Python 3.10 or newer is required and must execute Python code. Set AGENT_GOV_PYTHON to a supported interpreter or install Python 3.10+.");
  }
  return python;
}

function shouldSkip(sourcePath, root) {
  const relative = path.relative(root, sourcePath);
  const parts = relative.split(path.sep);
  if (parts.some((part) => IGNORE_DIRS.has(part))) {
    return true;
  }
  if (IGNORE_NAMES.has(path.basename(sourcePath))) {
    return true;
  }
  return IGNORE_SUFFIXES.has(path.extname(sourcePath));
}

function collectSkillFiles(root) {
  const files = [];
  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      const sourcePath = path.join(directory, entry.name);
      if (shouldSkip(sourcePath, root)) {
        continue;
      }
      if (entry.isSymbolicLink()) {
        throw new Error(`bundled skill contains unsupported symlink: ${sourcePath}`);
      }
      if (entry.isDirectory()) {
        walk(sourcePath);
      } else if (entry.isFile()) {
        files.push(sourcePath);
      }
    }
  }
  walk(root);
  return files.sort((left, right) => {
    const leftRelative = path.relative(root, left).split(path.sep).join("/");
    const rightRelative = path.relative(root, right).split(path.sep).join("/");
    return leftRelative < rightRelative ? -1 : leftRelative > rightRelative ? 1 : 0;
  });
}

function fileSha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath)).digest("hex");
}

function skillIdentity(skillRoot) {
  const digest = crypto.createHash("sha256");
  const files = collectSkillFiles(skillRoot);
  for (const filePath of files) {
    const relative = path.relative(skillRoot, filePath).split(path.sep).join("/");
    digest.update(relative, "utf8");
    digest.update("\0");
    digest.update(fileSha256(filePath), "ascii");
    digest.update("\0");
  }
  const skillMd = path.join(skillRoot, "SKILL.md");
  return {
    file_count: files.length,
    skill_md_sha256: fs.existsSync(skillMd) ? fileSha256(skillMd) : "",
    tree_sha256: digest.digest("hex"),
  };
}

function installManifest(skill, source) {
  const packageData = readPackage();
  const identity = skillIdentity(source);
  return {
    schema: "agent-gov-install-v1",
    package: packageData.name,
    package_version: packageData.version,
    skill,
    skill_md_sha256: identity.skill_md_sha256,
    tree_sha256: identity.tree_sha256,
    file_count: identity.file_count,
  };
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === "" || (!relative.startsWith(`..${path.sep}`) && relative !== ".." && !path.isAbsolute(relative));
}

function assertSafeDestination(boundaryRoot, destination) {
  const lexicalRoot = path.resolve(boundaryRoot);
  const lexicalDestination = path.resolve(destination);
  if (!isWithin(lexicalRoot, lexicalDestination)) {
    throw new Error(`install destination escapes selected scope: ${lexicalDestination}`);
  }
  const realBoundary = fs.existsSync(lexicalRoot) ? fs.realpathSync(lexicalRoot) : null;
  let current = lexicalRoot;
  const relative = path.relative(lexicalRoot, lexicalDestination);
  for (const part of relative.split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    let stat;
    try {
      stat = fs.lstatSync(current);
    } catch (error) {
      if (error.code === "ENOENT") {
        continue;
      }
      throw error;
    }
    if (!stat) {
      continue;
    }
    if (stat.isSymbolicLink()) {
      throw new Error(`install destination contains symlink: ${current}`);
    }
    const realCurrent = fs.realpathSync(current);
    if (realBoundary && !isWithin(realBoundary, realCurrent)) {
      throw new Error(`install destination resolves outside selected scope: ${current}`);
    }
  }
}

function copyTreeFresh(source, destination) {
  let copied = 0;
  fs.mkdirSync(destination, { recursive: true });
  for (const sourcePath of collectSkillFiles(source)) {
    const relative = path.relative(source, sourcePath);
    const destinationPath = path.join(destination, relative);
    fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
    fs.copyFileSync(sourcePath, destinationPath);
    fs.chmodSync(destinationPath, fs.statSync(sourcePath).mode & 0o777);
    copied += 1;
  }
  return copied;
}

function readInstallManifest(skillRoot) {
  try {
    return JSON.parse(fs.readFileSync(path.join(skillRoot, INSTALL_MANIFEST), "utf8"));
  } catch {
    return null;
  }
}

function validateInstalledSkill(skillRoot, expected) {
  if (!fs.existsSync(skillRoot)) {
    return { ok: false, detail: "missing target skill" };
  }
  const stat = fs.lstatSync(skillRoot);
  if (stat.isSymbolicLink()) {
    return { ok: false, detail: "target skill path is a symlink" };
  }
  if (!stat.isDirectory()) {
    return { ok: false, detail: "target skill path is not a directory" };
  }
  const manifest = readInstallManifest(skillRoot);
  if (!manifest || manifest.schema !== expected.schema) {
    return { ok: false, detail: "missing or invalid install identity manifest" };
  }
  for (const key of ["package", "package_version", "skill", "skill_md_sha256", "tree_sha256", "file_count"]) {
    if (manifest[key] !== expected[key]) {
      return { ok: false, detail: `install identity ${key} differs from bundled package` };
    }
  }
  let identity;
  try {
    identity = skillIdentity(skillRoot);
  } catch (error) {
    return { ok: false, detail: `cannot compute target skill identity: ${error.message}` };
  }
  if (identity.skill_md_sha256 !== expected.skill_md_sha256 || identity.tree_sha256 !== expected.tree_sha256 || identity.file_count !== expected.file_count) {
    return { ok: false, detail: "target skill content digest differs from install identity" };
  }
  return { ok: true, detail: `identity ${expected.tree_sha256.slice(0, 12)} package ${expected.package_version}` };
}

function prepareSkillInstall(source, destination, boundaryRoot, skill, options) {
  assertSafeDestination(boundaryRoot, destination);
  const expected = installManifest(skill, source);
  const fileCount = expected.file_count + 1;
  const exists = fs.existsSync(destination);
  if (exists) {
    const validation = validateInstalledSkill(destination, expected);
    if (validation.ok) {
      return {
        copied: 0,
        unchanged: fileCount,
        changed: false,
        commit() {},
        rollback() {},
      };
    }
    if (!options.force) {
      throw new Error(`skill install conflict at ${destination}: ${validation.detail}; review the existing skill and rerun with --force-skill or --force to replace it`);
    }
  }
  if (options.dryRun) {
    return {
      copied: fileCount,
      unchanged: 0,
      changed: false,
      commit() {},
      rollback() {},
    };
  }

  const parent = path.dirname(destination);
  fs.mkdirSync(parent, { recursive: true });
  assertSafeDestination(boundaryRoot, destination);
  const suffix = `${process.pid}-${crypto.randomBytes(6).toString("hex")}`;
  const stage = path.join(parent, `.${skill}.stage-${suffix}`);
  const backup = path.join(parent, `.${skill}.backup-${suffix}`);
  let movedExisting = false;
  try {
    copyTreeFresh(source, stage);
    fs.writeFileSync(path.join(stage, INSTALL_MANIFEST), `${JSON.stringify(expected, null, 2)}\n`, "utf8");
    const stagedValidation = validateInstalledSkill(stage, expected);
    if (!stagedValidation.ok) {
      throw new Error(`staged skill identity check failed: ${stagedValidation.detail}`);
    }
    if (exists) {
      fs.renameSync(destination, backup);
      movedExisting = true;
    }
    fs.renameSync(stage, destination);
  } catch (error) {
    fs.rmSync(stage, { recursive: true, force: true });
    if (movedExisting && !fs.existsSync(destination) && fs.existsSync(backup)) {
      fs.renameSync(backup, destination);
    }
    throw error;
  }
  return {
    copied: fileCount,
    unchanged: 0,
    changed: true,
    commit() {
      fs.rmSync(backup, { recursive: true, force: true });
    },
    rollback() {
      fs.rmSync(destination, { recursive: true, force: true });
      if (movedExisting && fs.existsSync(backup)) {
        fs.renameSync(backup, destination);
      }
    },
  };
}

function globalBoundaryRoot() {
  if (process.env.CODEX_HOME) {
    return path.resolve(process.env.CODEX_HOME);
  }
  const home = homeDir();
  if (!home) {
    throw new Error("cannot resolve global skill boundary: HOME, USERPROFILE, or CODEX_HOME is required");
  }
  return path.resolve(home);
}

function installSkills(targetRoot, options = {}) {
  const scope = options.global ? "global" : "project";
  const skillDest = options.global ? globalSkillDir() : path.join(targetRoot, ".codex", "skills");
  const boundaryRoot = options.global ? globalBoundaryRoot() : targetRoot;
  let copied = 0;
  let unchanged = 0;
  const transactions = [];
  try {
    for (const skill of RUNTIME_SKILLS) {
      const source = path.join(SKILLS_SOURCE, skill);
      const dest = path.join(skillDest, skill);
      const result = prepareSkillInstall(source, dest, boundaryRoot, skill, options);
      transactions.push(result);
      copied += result.copied;
      unchanged += result.unchanged;
    }
  } catch (error) {
    for (const transaction of [...transactions].reverse()) {
      transaction.rollback();
    }
    throw error;
  }
  console.log(`skill source: ${SKILLS_SOURCE}`);
  console.log(`skill scope: ${scope}`);
  console.log(`skill dest: ${skillDest}`);
  console.log(`skill files ${options.dryRun ? "would copy" : "copied"}: ${copied}`);
  console.log(`skill files unchanged: ${unchanged}`);
  console.log("skill file conflicts preserved: 0");
  return {
    commit() {
      for (const transaction of transactions) {
        transaction.commit();
      }
    },
    rollback() {
      for (const transaction of [...transactions].reverse()) {
        transaction.rollback();
      }
    },
  };
}

function bundledRegistryEntry() {
  const packageData = readPackage();
  const identity = skillIdentity(path.join(SKILLS_SOURCE, "agent-gov"));
  return {
    scope: "project",
    host: "codex",
    path: ".codex/skills/agent-gov",
    lifecycle: "active",
    intent: "project-governance",
    owner: "project-governance-owner",
    risk: "medium",
    source: {
      kind: "npm",
      repository: "https://www.npmjs.com/package/@airpot/agent-gov",
      ref: packageData.version,
      pinned: true,
    },
    content: {
      skill_md_sha256: identity.skill_md_sha256,
      tree_sha256: identity.tree_sha256,
    },
    release: {
      manifest: ".codex/skills/agent-gov/.agent-gov-install.json",
      publishable: false,
      release_gate: "package-install-identity",
    },
    review: {
      requires_review: false,
      latest_status: "not-required",
      latest_artifact: "",
    },
  };
}

function writeJsonAtomic(filePath, data) {
  const temporary = `${filePath}.tmp-${process.pid}-${crypto.randomBytes(6).toString("hex")}`;
  try {
    fs.writeFileSync(temporary, `${JSON.stringify(data, null, 2)}\n`, "utf8");
    fs.renameSync(temporary, filePath);
  } finally {
    fs.rmSync(temporary, { force: true });
  }
}

function loadProjectSkillRegistry(targetRoot) {
  const registryPath = path.join(targetRoot, ".agent", "project-skills.json");
  if (!fs.existsSync(registryPath)) {
    return null;
  }
  assertSafeDestination(targetRoot, registryPath);
  const original = fs.readFileSync(registryPath, "utf8");
  let registry;
  try {
    registry = JSON.parse(original);
  } catch (error) {
    throw new Error(`cannot use project skill registry: invalid ${registryPath}: ${error.message}`);
  }
  if (registry.schema !== "agent-project-skills-v1" || !registry.skills || typeof registry.skills !== "object" || Array.isArray(registry.skills)) {
    throw new Error(`cannot use project skill registry: unsupported schema at ${registryPath}`);
  }
  const existing = registry.skills["agent-gov"];
  if (existing && (existing.scope !== "project" || existing.host !== "codex" || existing.path !== ".codex/skills/agent-gov")) {
    throw new Error("cannot use project skill registry: existing agent-gov entry has a different scope, host, or path");
  }
  return { registryPath, original, registry };
}

function preflightProjectSkillRegistry(targetRoot) {
  if (!fs.existsSync(targetRoot)) {
    return;
  }
  loadProjectSkillRegistry(targetRoot);
}

function registerBundledProjectSkill(targetRoot) {
  const loaded = loadProjectSkillRegistry(targetRoot);
  if (!loaded) {
    return { reviewPending: false, commit() {}, rollback() {} };
  }
  const { registryPath, original, registry } = loaded;
  const targetSkill = path.join(targetRoot, ".codex", "skills", "agent-gov");
  const expectedManifest = installManifest("agent-gov", path.join(SKILLS_SOURCE, "agent-gov"));
  const validation = validateInstalledSkill(targetSkill, expectedManifest);
  if (!validation.ok) {
    throw new Error(`cannot register bundled skill: target install identity is invalid: ${validation.detail}`);
  }
  const packageEntry = bundledRegistryEntry();
  const existing = registry.skills["agent-gov"];
  const expected = existing
    ? {
        ...packageEntry,
        ...existing,
        scope: packageEntry.scope,
        host: packageEntry.host,
        path: packageEntry.path,
        source: packageEntry.source,
        content: packageEntry.content,
      }
    : packageEntry;
  const lifecycleChanged = Boolean(existing) && (
    existing?.source?.ref !== expected.source.ref
    || existing?.content?.skill_md_sha256 !== expected.content.skill_md_sha256
    || existing?.content?.tree_sha256 !== expected.content.tree_sha256
  );
  if (lifecycleChanged) {
    expected.review = {
      ...expected.review,
      requires_review: true,
      latest_status: "pending",
      latest_artifact: "",
    };
  }
  if (existing && JSON.stringify(existing) === JSON.stringify(expected)) {
    return { reviewPending: false, commit() {}, rollback() {} };
  }
  registry.skills["agent-gov"] = expected;
  registry.updated_at = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  writeJsonAtomic(registryPath, registry);
  return {
    reviewPending: lifecycleChanged,
    commit() {},
    rollback() {
      const temporary = `${registryPath}.rollback-${process.pid}-${crypto.randomBytes(6).toString("hex")}`;
      try {
        fs.writeFileSync(temporary, original, "utf8");
        fs.renameSync(temporary, registryPath);
      } finally {
        fs.rmSync(temporary, { force: true });
      }
    },
  };
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

function initRootSelection(args) {
  let root = null;
  let rootIndex = -1;
  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];
    if (arg === "--") {
      if (index + 1 < args.length && root === null) {
        root = args[index + 1];
        rootIndex = index + 1;
      }
      break;
    }
    if (INIT_VALUE_OPTIONS.has(arg)) {
      index += 1;
      continue;
    }
    if (arg.startsWith("--") && arg.includes("=")) {
      continue;
    }
    if (!arg.startsWith("-") && root === null) {
      root = arg;
      rootIndex = index;
    }
  }
  return { root: root ?? ".", rootIndex };
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
    if (!fs.statSync(targetRoot).isDirectory()) {
      throw new Error(`target root is not a directory: ${targetRoot}`);
    }
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
    } else if (arg === "--global") {
      throw new Error("--global is only supported by install-skill; project initialization requires a project-local bundled skill");
    } else {
      passthrough.push(arg);
    }
  }
  return { passthrough, skipSkillInstall, forceSkill };
}

function runInitializer(args, python, stdio = "inherit") {
  if (!fs.existsSync(INIT_SCRIPT)) {
    throw new Error(`initializer missing from npm package: ${INIT_SCRIPT}`);
  }
  const result = spawnSync(
    python.command,
    [...python.args, INIT_SCRIPT, ...args],
    { cwd: process.cwd(), stdio, encoding: stdio === "pipe" ? "utf8" : undefined },
  );
  if (result.error) {
    throw result.error;
  }
  return result;
}

function init(args) {
  const { passthrough, skipSkillInstall, forceSkill } = splitInitArgs(args);
  if (passthrough.includes("--help") || passthrough.includes("-h")) {
    printHelp();
    return 0;
  }
  const rootSelection = initRootSelection(passthrough);
  const rootArg = rootSelection.root;
  const targetRoot = path.resolve(process.cwd(), rootArg);
  const dryRun = passthrough.includes("--dry-run");
  const force = forceSkill || passthrough.includes("--force");
  const initializerArgs = rootSelection.rootIndex >= 0 ? passthrough : [targetRoot, ...passthrough];
  const python = requirePython();
  preflightProjectSkillRegistry(targetRoot);
  const preflightArgs = dryRun ? initializerArgs : [...initializerArgs, "--dry-run"];
  const preflight = runInitializer(preflightArgs, python, "pipe");
  if ((preflight.status ?? 1) !== 0) {
    process.stdout.write(preflight.stdout || "");
    process.stderr.write(preflight.stderr || "");
    return preflight.status ?? 1;
  }
  if (dryRun) {
    ensureTargetRoot(targetRoot, passthrough, true);
    if (!skipSkillInstall) {
      installSkills(targetRoot, { force, dryRun: true });
    }
    process.stdout.write(preflight.stdout || "");
    return 0;
  }

  ensureTargetRoot(targetRoot, passthrough, false);
  const transaction = skipSkillInstall ? null : installSkills(targetRoot, { force, dryRun: false });
  const result = runInitializer(initializerArgs, python);
  const status = result.status ?? 1;
  if (status === 0) {
    let registryTransaction = null;
    try {
      registryTransaction = skipSkillInstall ? null : registerBundledProjectSkill(targetRoot);
      transaction?.commit();
      registryTransaction?.commit();
      if (registryTransaction?.reviewPending) {
        console.log("project skill review pending: agent-gov lifecycle identity changed; complete review-fix-review before readiness");
      }
    } catch (error) {
      registryTransaction?.rollback();
      transaction?.rollback();
      throw error;
    }
  } else {
    transaction?.rollback();
  }
  return status;
}

function installSkill(args) {
  const options = parseInstallArgs(args);
  const targetRoot = path.resolve(process.cwd(), options.target);
  if (!options.global) {
    ensureTargetRoot(targetRoot, [], options.dryRun);
  }
  const transaction = installSkills(targetRoot, options);
  let registryTransaction = null;
  try {
    registryTransaction = options.global || options.dryRun ? null : registerBundledProjectSkill(targetRoot);
    transaction.commit();
    registryTransaction?.commit();
    if (registryTransaction?.reviewPending) {
      console.log("project skill review pending: agent-gov lifecycle identity changed; complete review-fix-review before readiness");
    }
  } catch (error) {
    registryTransaction?.rollback();
    transaction.rollback();
    throw error;
  }
  return 0;
}

function doctor(args) {
  const targetRoot = path.resolve(process.cwd(), firstPositional(args));
  const python = findPython();
  const targetSkill = path.join(targetRoot, ".codex", "skills", "agent-gov");
  let targetIdentity = { ok: false, detail: "target root is missing" };
  if (fs.existsSync(targetRoot)) {
    try {
      assertSafeDestination(targetRoot, targetSkill);
      targetIdentity = validateInstalledSkill(
        targetSkill,
        installManifest("agent-gov", path.join(SKILLS_SOURCE, "agent-gov")),
      );
    } catch (error) {
      targetIdentity = { ok: false, detail: error.message };
    }
  }
  console.log("agent-gov doctor checks package/install health, not target project implementation readiness.");
  console.log("Use `agent-gov readiness <root>` for strict generated-project readiness gates.");
  const checks = [
    ["package", fs.existsSync(PACKAGE_JSON), PACKAGE_JSON],
    ["initializer", fs.existsSync(INIT_SCRIPT), INIT_SCRIPT],
    ["bundled agent-gov skill", fs.existsSync(path.join(SKILLS_SOURCE, "agent-gov", "SKILL.md")), path.join(SKILLS_SOURCE, "agent-gov")],
    ["python >=3.10", Boolean(python), python ? `${python.command} ${python.args.join(" ")}`.trim() : "missing or unsupported"],
    ["target root", fs.existsSync(targetRoot), targetRoot],
    ["target agent-gov skill", targetIdentity.ok, `${targetSkill} (${targetIdentity.detail})`],
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

function readiness(args) {
  const targetRoot = path.resolve(process.cwd(), firstPositional(args));
  const python = requirePython();
  const checkScript = path.join(targetRoot, "scripts", "agent_check.py");
  if (!fs.existsSync(checkScript)) {
    throw new Error(`target project readiness check is missing: ${checkScript}`);
  }
  console.log("agent-gov readiness checks generated-project implementation readiness.");
  console.log("Package/install health remains available through `agent-gov doctor <root>`.");
  const result = spawnSync(
    python.command,
    [...python.args, "scripts/agent_check.py", "--strict"],
    { cwd: targetRoot, stdio: "inherit" },
  );
  if (result.error) {
    throw result.error;
  }
  return result.status ?? 1;
}

function main(argv) {
  const commands = new Set(["init", "install-skill", "doctor", "readiness", "help", "version"]);
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
  if (command === "readiness") {
    return readiness(args);
  }
  return init(args);
}

try {
  process.exitCode = main(process.argv.slice(2));
} catch (error) {
  console.error(`agent-gov: ${error.message}`);
  process.exitCode = 1;
}
