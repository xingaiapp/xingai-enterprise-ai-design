import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";

const roots = [
  "deep-enterprise-ai",
  "enterprise-poc/docs",
  "enterprise-poc/README.md",
  "enterprise-poc/README.zh.md",
];
const files = [];
const failures = [];

function walk(target) {
  if (statSync(target).isDirectory()) {
    for (const name of readdirSync(target)) walk(join(target, name));
  } else if (target.endsWith(".md")) {
    files.push(target);
  }
}

for (const root of roots) walk(root);

for (const file of files) {
  const content = readFileSync(file, "utf8");
  const peer = file.endsWith(".zh.md")
    ? file.replace(/\.zh\.md$/, ".md")
    : file.replace(/\.md$/, ".zh.md");
  if (!existsSync(peer)) failures.push(`${file}: missing bilingual peer ${peer}`);

  for (const match of content.matchAll(/\[[^\]]*\]\(([^)]+)\)/g)) {
    const target = match[1].split("#")[0];
    if (!target || target.startsWith("*") || /^(https?:|mailto:)/.test(target)) continue;
    if (!existsSync(resolve(dirname(file), target))) failures.push(`${file}: broken link ${target}`);
  }

  for (const match of content.matchAll(/```python\n([\s\S]*?)```/g)) {
    const result = spawnSync(
      "python3",
      ["-c", "import sys; compile(sys.stdin.read(), 'lesson', 'exec')"],
      { input: match[1], encoding: "utf8" },
    );
    if (result.status !== 0) failures.push(`${file}: invalid Python snippet: ${result.stderr.trim()}`);
  }
}

const courseDirs = readdirSync("deep-enterprise-ai").filter((name) => /^\d\d-/.test(name));
for (const courseDir of courseDirs) {
  for (const name of ["README.md", "README.zh.md"]) {
    const file = join("deep-enterprise-ai", courseDir, name);
    const content = readFileSync(file, "utf8");
    for (const marker of ["5W + How", "```mermaid"]) {
      if (!content.includes(marker)) failures.push(`${file}: missing ${marker}`);
    }
    if (!/```(python|yaml)/.test(content)) failures.push(`${file}: missing code example`);
  }
  for (const name of ["lab.md", "lab.zh.md"]) {
    const file = join("deep-enterprise-ai", courseDir, name);
    if (!existsSync(file)) failures.push(`${file}: missing lab`);
  }
}

if (failures.length) {
  console.error(failures.join("\n"));
  process.exit(1);
}

console.log(
  `Verified ${files.length} documents, ${courseDirs.length} bilingual courses, labs, links, diagrams, and Python snippets.`,
);
