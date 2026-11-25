// Draws my kodama bonsai with winter forced on, using kodama's own engine.
//
// kodama (github.com/orijitghosh/kodama, MIT) decides the season from the calendar month, so it
// keeps autumn leaves until 1 December. This renders the same tree from the same public history,
// with the season set to winter and both snow events on: snow settled on the pads and pot rim,
// and flakes falling. Everything else (growth, pot, streak, ornaments) is kodama's logic as is.
//
//   node scripts/winter_kodama.mjs <engine dist dir> <user> <out.svg> [history.json]
import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";

const [engineDir, user, out, historyFile] = process.argv.slice(2);
const engine = await import(pathToFileURL(path.resolve(engineDir, "index.js")).href);

const body = historyFile
  ? JSON.parse(await readFile(historyFile, "utf8"))
  : await (await fetch(`https://kodama-sigma.vercel.app/api/${user}.json`)).json();
if (!body.history) throw new Error(`no history for ${user}: ${JSON.stringify(body).slice(0, 200)}`);

// Read by the patched seasonFor / seasonalEventsFor in the engine's facts.ts. Only November is
// pulled forward: from 1 December kodama's calendar says winter itself, and this is plain kodama.
const today = new Date().toISOString().slice(0, 10);
if (today.slice(5, 7) === "11") {
  globalThis.KODAMA_SEASON = "winter";
  globalThis.KODAMA_EVENTS = [{ kind: "firstSnow" }, { kind: "settledSnow" }];
}

const svg = engine.render(body.history, today, {
  biome: "bonsai",
  theme: "ink",
  scale: "full",
  animate: true,
  tint: "lang",
  species: "classic",
  locale: "en",
});
await writeFile(out, svg);
console.log(`wrote ${out} (${svg.length} bytes)`);
