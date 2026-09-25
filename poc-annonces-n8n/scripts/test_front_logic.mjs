import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../front/index.html", import.meta.url), "utf8");
const m = html.match(/\/\/ <logic>([\s\S]*?)\/\/ <\/logic>/);
assert.ok(m, "bloc // <logic> introuvable dans front/index.html");
const L = new Function(m[1] + "\nreturn { PLAN_LABELS, PLAN_ORDER, stepOf, moodUnion, filterByMoods, cleanErr, journalLines, summarize };")();

const item = (id, moods, actif = true) => ({ drive_file_id: id, moods, actif });

test("stepOf : parcours normal", () => {
  assert.equal(L.stepOf(null), 1);
  for (const s of ["texte_en_cours", "texte_pret"]) assert.equal(L.stepOf({ statut: s }), 1);
  for (const s of ["selection_en_cours", "en_attente_validation"]) assert.equal(L.stepOf({ statut: s }), 2);
  for (const s of ["generation_en_cours", "premiere_prete", "galerie_prete", "budget_depasse", "termine"]) assert.equal(L.stepOf({ statut: s }), 3);
});

test("stepOf : une erreur reste à l'étape qui l'a produite", () => {
  assert.equal(L.stepOf({ statut: "erreur", erreur: "Texte : boom", titre: "" }), 1);
  assert.equal(L.stepOf({ statut: "erreur", erreur: "Texte : boom", titre: "T" }), 1);
  assert.equal(L.stepOf({ statut: "erreur", erreur: "Style : boom", titre: "T" }), 2);
  assert.equal(L.stepOf({ statut: "erreur", erreur: "", titre: "" }), 1);
});

test("moodUnion : union triée par fréquence, sans doublon", () => {
  const items = [item("a", ["parisian_chic", "vintage_retro"]), item("b", ["parisian_chic"]), item("c", ["streetwear_decontracte"])];
  assert.deepEqual(L.moodUnion(items, ["a", "b", "c"]), ["parisian_chic", "streetwear_decontracte", "vintage_retro"]);
  assert.deepEqual(L.moodUnion(items, ["a"]), ["parisian_chic", "vintage_retro"]);
  assert.deepEqual(L.moodUnion(items, []), []);
  assert.deepEqual(L.moodUnion(items, ["inconnu"]), []);
});

test("filterByMoods : au moins un mood coché, actifs seulement, aucun filtre = tout", () => {
  const items = [item("a", ["x", "y"]), item("b", ["y"]), item("c", ["z"]), item("d", ["x"], false)];
  assert.deepEqual(L.filterByMoods(items, ["x"]).map(i => i.drive_file_id), ["a"]);
  assert.deepEqual(L.filterByMoods(items, ["x", "z"]).map(i => i.drive_file_id), ["a", "c"]);
  assert.deepEqual(L.filterByMoods(items, []).map(i => i.drive_file_id), ["a", "b", "c"]);
});

test("cleanErr retire le préfixe d'étape", () => {
  assert.equal(L.cleanErr("Photos : délai dépassé"), "délai dépassé");
  assert.equal(L.cleanErr("Texte : x"), "x");
  assert.equal(L.cleanErr("autre"), "autre");
  assert.equal(L.cleanErr(undefined), "");
});

const job = (over) => Object.assign({ job_id: "j1", statut: "texte_en_cours", erreur: "", cout_total: 0, plans: [
  { plan: "porte_miroir", statut: "en_attente" }, { plan: "cintre", statut: "en_attente" }, { plan: "detail", statut: "en_attente" }] }, over);
const withPlans = (states) => ({ plans: ["porte_miroir", "cintre", "detail"].map((plan, i) => Object.assign({ plan, statut: "en_attente" }, states[i] || {})) });

test("journalLines : texte", () => {
  assert.deepEqual(L.journalLines(null, job()).map(l => l.text), ["Lecture des photos…"]);
  const l = L.journalLines(job(), job({ statut: "texte_pret" }));
  assert.deepEqual(l.map(x => [x.text, x.kind]), [["Annonce prête ✓", "ok"]]);
  assert.deepEqual(L.journalLines(job(), job()), []);
});

test("journalLines : sélection puis génération en deux temps", () => {
  assert.equal(L.journalLines(job({ statut: "texte_pret" }), job({ statut: "selection_en_cours" }))[0].text, "Recherche des inspirations dans la bibliothèque…");
  assert.equal(L.journalLines(job({ statut: "selection_en_cours" }), job({ statut: "en_attente_validation" }))[0].kind, "ok");
  assert.equal(L.journalLines(job({ statut: "en_attente_validation" }), job({ statut: "generation_en_cours" }))[0].text, "Génération de la photo portée (1/3)…");
  const prev = job({ statut: "generation_en_cours" });
  const cur = job({ statut: "premiere_prete", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  assert.deepEqual(L.journalLines(prev, cur).map(l => l.text), ["Photo « Porté » prête (1/3) ✓ 0.08 $", "Première photo prête : à toi de la valider."]);
  const s2 = job({ statut: "generation_en_cours", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  assert.equal(L.journalLines(cur, s2, { suiteAsked: true })[0].text, "Génération des photos 2/3 et 3/3…");
  assert.equal(L.journalLines(cur, s2)[0].text, "Nouvelle tentative de la photo portée…");
  assert.equal(L.journalLines(cur, s2, { suiteAsked: false })[0].text, "Nouvelle tentative de la photo portée…");
});

test("journalLines : galerie prête, erreurs de plan et d'étape", () => {
  const prev = job({ statut: "generation_en_cours", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  const cur = job({ statut: "galerie_prete", cout_total: 0.2402, ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "pret", tentative: 1, cout_plan: 0.08 }]) });
  assert.deepEqual(L.journalLines(prev, cur).map(l => l.text), ["Photo « Détail » prête (3/3) ✓ 0.08 $", "Les 3 photos sont prêtes ✓ (coût total 0.24 $)"]);
  const errPlan = job({ statut: "galerie_prete", ...withPlans([{ statut: "pret", tentative: 1, cout_plan: 0.08 }, { statut: "erreur", erreur: "Photos : délai dépassé" }]) });
  assert.ok(L.journalLines(job({ statut: "generation_en_cours" }), errPlan).some(l => l.kind === "err" && l.text === "⚠ Photo « Sur cintre » : délai dépassé"));
  const errJob = L.journalLines(job(), job({ statut: "erreur", erreur: "Texte : boom" }));
  assert.ok(errJob.some(l => l.kind === "err" && l.text === "⚠ Texte : boom"));
});

test("journalLines : régénération d'une photo", () => {
  const ready = withPlans([{ statut: "pret", tentative: 1 }, { statut: "pret", tentative: 1 }, { statut: "pret", tentative: 1 }]);
  const l = L.journalLines(job({ statut: "galerie_prete", ...ready }), job({ statut: "generation_en_cours", ...ready }));
  assert.equal(l[0].text, "Régénération d'une photo…");
});

test("summarize : période, totaux, images et régénérations", () => {
  const now = new Date("2026-09-25T12:00:00Z").getTime();
  const jobs = [
    { created_at: "2026-09-24T10:00:00Z", cout_texte: 0.0002, cout_images: 0.24, cout_total: 0.2402, nb_images: 3, nb_regenerations: 0 },
    { created_at: "2026-09-10T10:00:00Z", cout_texte: 0.0002, cout_images: 0.4, cout_total: 0.4002, nb_images: 5, nb_regenerations: 2 },
    { created_at: "2026-08-01T10:00:00Z", cout_texte: 0, cout_images: 0, cout_total: 0, nb_images: 0, nb_regenerations: 0 }
  ];
  const s7 = L.summarize(jobs, 7, now), s30 = L.summarize(jobs, 30, now), all = L.summarize(jobs, 0, now);
  assert.equal(s7.fiches, 1); assert.equal(s30.fiches, 2); assert.equal(all.fiches, 3);
  assert.equal(s30.images, 8); assert.equal(s30.regenerations, 2);
  assert.equal(Math.round(s30.cout_total * 10000), 6404);
  assert.equal(all.list.length, 3);
});
