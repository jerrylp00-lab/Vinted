import { readFileSync } from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

const html = readFileSync(new URL("../front/index.html", import.meta.url), "utf8");
const m = html.match(/\/\/ <logic>([\s\S]*?)\/\/ <\/logic>/);
assert.ok(m, "bloc // <logic> introuvable dans front/index.html");
const L = new Function(m[1] + "\nreturn { fmtUsd, isBusy, viewOf, statusLabel, validateLabel, listingMeta, totalsOf };")();

const img = (idx, ok = true) => ({ idx, essai: 1, drive_file_id: ok ? "f" + idx : "", erreur: ok ? "" : "boom" });

test("fmtUsd : virgule française", () => {
  assert.equal(L.fmtUsd(0.08), "0,08 $");
  assert.equal(L.fmtUsd(undefined), "0,00 $");
});

test("isBusy : seuls les statuts en cours", () => {
  assert.equal(L.isBusy(null), false);
  for (const s of ["test_en_cours", "lot_en_cours"]) assert.equal(L.isBusy({ statut: s }), true);
  for (const s of ["test_pret", "test_erreur", "termine"]) assert.equal(L.isBusy({ statut: s }), false);
});

test("viewOf : test prêt = validation et feedback possibles, pas d'annonce", () => {
  const v = L.viewOf({ statut: "test_pret", n: 3, images: [img(0)] });
  assert.equal(v.showTest, true); assert.equal(v.canValidate, true); assert.equal(v.canFeedback, true); assert.equal(v.showListing, false);
});

test("viewOf : test prêt mais sans image = pas de validation", () => {
  assert.equal(L.viewOf({ statut: "test_pret", n: 3, images: [img(0, false)] }).canValidate, false);
});

test("viewOf : test en cours = rien d'actionnable", () => {
  const v = L.viewOf({ statut: "test_en_cours", n: 3, images: [] });
  assert.equal(v.canValidate, false); assert.equal(v.canFeedback, false);
});

test("viewOf : test en erreur = feedback possible (relance), pas de validation", () => {
  const v = L.viewOf({ statut: "test_erreur", n: 3, images: [img(0, false)] });
  assert.equal(v.canFeedback, true); assert.equal(v.canValidate, false);
});

test("viewOf : lot en cours = annonce visible, progression du lot", () => {
  const v = L.viewOf({ statut: "lot_en_cours", n: 4, images: [img(0), img(1), img(2, false)] });
  assert.equal(v.showListing, true); assert.equal(v.lotDone, 1); assert.equal(v.lotExpected, 3); assert.equal(v.canFeedback, false);
});

test("viewOf : terminé = annonce et feedback général", () => {
  const v = L.viewOf({ statut: "termine", n: 2, images: [img(0), img(1)] });
  assert.equal(v.showListing, true); assert.equal(v.canFeedback, true); assert.equal(v.canValidate, false);
});

test("statusLabel : lot avec compteur", () => {
  assert.match(L.statusLabel({ statut: "lot_en_cours", n: 3, images: [img(0), img(1)] }), /\(1\/2\)/);
  assert.equal(L.statusLabel({ statut: "termine", n: 1, images: [] }), "Annonce prête ✓");
});

test("validateLabel : nombre d'images restantes et coût estimé", () => {
  assert.equal(L.validateLabel({ n: 3 }, 0.1), "Valider et générer les 2 autres (≈ 0,20 $)");
  assert.equal(L.validateLabel({ n: 1 }, 0.1), "Valider et rédiger le texte");
});

test("listingMeta : uniquement les champs renseignés", () => {
  assert.equal(L.listingMeta({ marque: "Zara", taille: "M", mesures: "" }), "Marque : Zara · Taille : M");
  assert.equal(L.listingMeta({}), "");
});

test("totalsOf : cumule annonces, images et coûts", () => {
  const t = L.totalsOf([{ nb_images: 3, cout_total: 0.25 }, { nb_images: 2, cout_total: 0.5 }]);
  assert.equal(t.runs, 2); assert.equal(t.images, 5); assert.ok(Math.abs(t.cout - 0.75) < 1e-9);
});
