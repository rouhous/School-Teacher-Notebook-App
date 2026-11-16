import { readFileSync, writeFileSync } from "node:fs";
import { join, basename } from "node:path";

const [version, inputFile] = process.argv.slice(2);
const root = process.cwd();
const addonId = "noor-prep-filler-private-2026@rouhous.github.io";
const baseUrl = "https://rouhous.github.io/School-Teacher-Notebook-App/addons/files/";
const filename = basename(inputFile || "");

if (!/^\d+\.\d+\.\d+$/.test(version || "")) throw Error("Invalid add-on version");
if (filename !== "Noor-Unified-v" + version + "-signed.xpi") throw Error("Unexpected XPI filename");
const toParts = s => s.split(".").map(Number);
const compare = (a, b) => {
  const x = toParts(a), y = toParts(b);
  return x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
};

const updatesPath = join(root, "addons/updates.json");
const updatesJson = JSON.parse(readFileSync(updatesPath, "utf8"));
const addon = updatesJson.addons?.[addonId];
if (!addon || !Array.isArray(addon.updates)) throw Error("Unexpected update feed structure");
const versions = addon.updates.map(x => x.version);
if (versions.some(v => compare(version, v) <= 0))
  throw Error("Release " + version + " must be newer than published versions: " + versions.join(", "));

addon.updates.push({
  version,
  update_link: baseUrl + encodeURIComponent(filename),
  applications: { gecko: { strict_min_version: "140.0" } }
});
addon.updates.sort((a, b) => compare(a.version, b.version));
writeFileSync(updatesPath, JSON.stringify(updatesJson, null, 2) + "\n");

const pagePath = join(root, "addons/index.html");
let page = readFileSync(pagePath, "utf8");
const installLink = /(<a\b[^>]*\bid="install-xpi"[^>]*\bhref=")[^"]*(")/;
if (!installLink.test(page)) throw Error("Install link not found in library HTML");
page = page.replace(installLink, (_, left, right) => left + "./files/" + filename + right);

const androidDownload = /(link\.setAttribute\(\s*'download'\s*,\s*')[^']+('\s*\))/;
if (!androidDownload.test(page)) throw Error("Android download handler not found");
page = page.replace(androidDownload, (_, left, right) => left + filename + right);
writeFileSync(pagePath, page);

writeFileSync(join(root, "addons/latest.json"), JSON.stringify({
  id: addonId,
  version,
  download_url: baseUrl + encodeURIComponent(filename),
  published_at: new Date().toISOString()
}, null, 2) + "\n");
console.log("Prepared site install link and updates.json for signed version " + version);
