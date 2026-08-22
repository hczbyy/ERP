/* 前端静态资源完整性自检：HTML 引用 vs 磁盘文件、CSS 括号配对 */
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "..", "..", "frontend");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");

// 1. 检查所有 src/href 引用
const refs = [...html.matchAll(/(?:src|href)="([^"]+)"/g)].map((m) => m[1]);
let missing = 0;
for (const r of refs) {
  const full = path.join(root, r);
  if (!fs.existsSync(full)) {
    console.log(`MISSING  ${r}`);
    missing++;
  }
}
console.log(`\nHTML 引用 ${refs.length} 个，缺失 ${missing} 个`);

// 2. CSS 花括号配对
const css = fs.readFileSync(path.join(root, "css", "app.css"), "utf8");
let depth = 0, line = 1, bad = false;
for (const ch of css) {
  if (ch === "\n") line++;
  if (ch === "{") depth++;
  if (ch === "}") depth--;
  if (depth < 0) { console.log(`CSS 括号不匹配，第 ${line} 行`); bad = true; break; }
}
if (!bad && depth !== 0) { console.log(`CSS 花括号未闭合，剩余 ${depth} 个`); bad = true; }
if (!bad) console.log("CSS 花括号配对 OK");
process.exit(bad || missing ? 1 : 0);