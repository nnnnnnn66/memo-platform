"""MOTEUR DE CALCUL DÉTERMINISTE — les chiffres viennent du code, jamais du modèle.

C'est la garantie anti-invention de l'étape 10 : toutes les valeurs publiées dans la sortie proviennent
d'ici. Bibliothèque standard uniquement (aucune dépendance scientifique), aucun accès réseau, aucune
écriture de fichier.

Ce que le moteur produit, à partir des données RÉELLEMENT fournies :
  - profilage : lignes, colonnes, nature des variables, valeurs manquantes, doublons ;
  - statistiques descriptives : effectif, moyenne, médiane, minimum, maximum, étendue ;
  - effectifs et fréquences (avec pourcentage) par modalité d'une variable catégorielle ;
  - croisements : moyenne d'une variable numérique par groupe d'une variable catégorielle.

Chaque résultat reçoit un identifiant `R<n>` que le modèle doit citer : un résultat affirmé sans
référence est refusé (contrôle Q1), et un chiffre absent du moteur est détecté (contrôle Q2).
"""

import csv
import io
import re
import statistics
import unicodedata
from collections import Counter, defaultdict

MAX_ROWS = 2000           # borne de sécurité : au-delà, l'étudiant doit agréger en amont
_MAX_RESULTS = 400        # borne du nombre de résultats produits


def _normalize_decimal(text: str) -> str:
    """« 3,4 » (virgule décimale française) → « 3.4 »."""
    return str(text).strip().replace("\u00a0", "").replace(" ", "").replace(",", ".")


def _as_number(value) -> float | None:
    raw = _normalize_decimal(value)
    raw = re.sub(r"[%€$]", "", raw)
    if not raw or not re.fullmatch(r"[-+]?\d*\.?\d+", raw):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _fmt(value: float) -> str:
    """Formatage français court : 3.4 → « 3,4 » ; 42.0 → « 42 »."""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def parse_table(contenu: str) -> tuple[list[str], list[list[str]]]:
    """Détecte le séparateur et lit un tableau CSV. Retourne (en-têtes, lignes)."""
    text = (contenu or "").strip()
    if not text:
        return [], []
    first = text.splitlines()[0]
    delimiter = max((",", ";", "\t", "|"), key=first.count)
    if first.count(delimiter) == 0:
        # Pas d'en-tête détectable : une seule colonne.
        rows = [[line.strip()] for line in text.splitlines() if line.strip()]
        return (["valeur"] if rows else []), rows
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [row for row in reader if any(str(cell).strip() for cell in row)]
    if not rows:
        return [], []
    header = [str(cell).strip() or f"colonne_{i + 1}" for i, cell in enumerate(rows[0])]
    return header, rows[1:]


def profile(contenu: str) -> dict:
    """Profil d'un jeu de données : variables, manquants, doublons (aucune transformation)."""
    header, rows = parse_table(contenu)
    rows = rows[:MAX_ROWS]
    columns: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for index, name in enumerate(header):
            columns[name].append(str(row[index]).strip() if index < len(row) else "")

    variables = []
    for name, values in columns.items():
        present = [v for v in values if v]
        numeric = [v for v in present if _as_number(v) is not None]
        nature = "numerique" if present and len(numeric) == len(present) else (
            "categorielle" if 0 < len(set(present)) <= max(2, len(present) // 2) else "texte")
        variables.append({
            "nom": name, "nature": nature, "manquants": len(values) - len(present),
            "modalites": sorted(set(present))[:20],
        })

    seen: Counter = Counter(tuple(row) for row in rows)
    doublons = sum(count - 1 for count in seen.values() if count > 1)
    return {"lignes": len(rows), "variables": variables, "doublons": doublons,
            "colonnes": len(header)}


def _add(results: list[dict], libelle: str, valeur: str, effectif: int, methode: str,
         variable: str = "", groupe: str = "", unite: str = "") -> None:
    if len(results) >= _MAX_RESULTS:
        return
    results.append({
        "id": f"R{len(results) + 1}", "libelle": libelle, "valeur": valeur, "unite": unite,
        "effectif": effectif, "methode": methode, "variable": variable, "groupe": groupe,
    })


def compute(contenu: str, nom_dataset: str = "") -> list[dict]:
    """Calcule tous les résultats descriptifs d'un tableau fourni."""
    header, rows = parse_table(contenu)
    if not header:
        return []
    rows = rows[:MAX_ROWS]
    prefix = f"{nom_dataset} — " if nom_dataset else ""
    results: list[dict] = []

    _add(results, f"{prefix}nombre de lignes analysées", _fmt(len(rows)), len(rows),
         "effectif_total", variable="")

    numeric_columns: dict[str, list[float]] = {}
    categorical_columns: dict[str, list[str]] = {}
    #: Colonnes d'identification : les décrire par une moyenne n'a aucun sens et pollue la sortie.
    _IDENTIFIANTS = {"id", "identifiant", "numero", "num", "code", "no", "n", "ref", "reference"}
    for index, name in enumerate(header):
        if _slug(name) in _IDENTIFIANTS:
            continue
        values = [str(row[index]).strip() if index < len(row) else "" for row in rows]
        present = [v for v in values if v]
        numbers = [(_as_number(v), v) for v in present]
        if present and all(number is not None for number, _ in numbers):
            numeric_columns[name] = [number for number, _ in numbers]
        elif present:
            categorical_columns[name] = present
        missing = len(values) - len(present)
        if missing:
            _add(results, f"{prefix}valeurs manquantes — {name}", _fmt(missing), len(values),
                 "valeurs_manquantes", variable=name, unite="réponses")

    for name, numbers in numeric_columns.items():
        if not numbers:
            continue
        _add(results, f"{prefix}effectif — {name}", _fmt(len(numbers)), len(numbers),
             "effectif", variable=name)
        _add(results, f"{prefix}moyenne — {name}", _fmt(statistics.fmean(numbers)), len(numbers),
             "moyenne", variable=name)
        _add(results, f"{prefix}médiane — {name}", _fmt(statistics.median(numbers)), len(numbers),
             "mediane", variable=name)
        _add(results, f"{prefix}minimum — {name}", _fmt(min(numbers)), len(numbers),
             "minimum", variable=name)
        _add(results, f"{prefix}maximum — {name}", _fmt(max(numbers)), len(numbers),
             "maximum", variable=name)
        _add(results, f"{prefix}étendue — {name}", _fmt(max(numbers) - min(numbers)), len(numbers),
             "etendue", variable=name)

    for name, values in categorical_columns.items():
        counts = Counter(values)
        total = len(values)
        for modality, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
            pourcentage = (count / total * 100) if total else 0.0
            _add(results, f"{prefix}effectif — {name} = {modality}", _fmt(count), total,
                 "effectif_modalite", variable=name, groupe=str(modality), unite="réponses")
            _add(results, f"{prefix}fréquence — {name} = {modality}", f"{_fmt(pourcentage)} %",
                 total, "frequence", variable=name, groupe=str(modality), unite="%")

    # Croisements : moyenne d'une variable numérique par groupe d'une variable catégorielle.
    for cat_name, cat_values in list(categorical_columns.items())[:3]:
        index_cat = header.index(cat_name)
        for num_name, _ in list(numeric_columns.items())[:3]:
            index_num = header.index(num_name)
            groups: dict[str, list[float]] = defaultdict(list)
            for row in rows:
                value = str(row[index_num]).strip() if index_num < len(row) else ""
                number = _as_number(value)
                groupe = str(row[index_cat]).strip() if index_cat < len(row) else ""
                if number is not None and groupe:
                    groups[groupe].append(number)
            for groupe, numbers in sorted(groups.items())[:12]:
                if not numbers:
                    continue
                _add(results, f"{prefix}moyenne — {num_name} pour {cat_name} = {groupe}",
                     _fmt(statistics.fmean(numbers)), len(numbers), "moyenne_par_groupe",
                     variable=num_name, groupe=groupe)
    return results


def compute_documents(documents: list) -> list[dict]:
    """Résultats sur un corpus documentaire : nombre de documents, périodes couvertes."""
    results: list[dict] = []
    if not documents:
        return results
    _add(results, "nombre de documents étudiés", _fmt(len(documents)), len(documents),
         "effectif_total")
    periods = sorted({str(getattr(d, "periode", "") or "").strip()
                      for d in documents if str(getattr(d, "periode", "") or "").strip()})
    if periods:
        _add(results, "périodes couvertes par le corpus", " ; ".join(periods[:10]), len(periods),
             "inventaire", variable="periode")
    types = Counter(str(getattr(d, "type", "") or "non précisé").strip() for d in documents)
    for type_name, count in sorted(types.items()):
        _add(results, f"effectif — documents de type {type_name}", _fmt(count), len(documents),
             "effectif_modalite", variable="type_document")
    return results


def derived_percentages(results: list[dict]) -> set[str]:
    """Pourcentages que le modèle peut légitimement déduire des effectifs calculés."""
    allowed: set[str] = set()
    for resultat in results:
        try:
            value = float(str(resultat.get("valeur", "")).replace(",", "."))
            effectif = int(resultat.get("effectif", 0) or 0)
        except (TypeError, ValueError):
            continue
        if effectif > 0 and "effectif" in str(resultat.get("methode", "")):
            allowed.add(_fmt(value / effectif * 100))
    return allowed


def numeric_whitelist(computed: list[dict], sources: list[str]) -> set[str]:
    """Valeurs autorisées dans le texte produit : calculées, fournies, années, pourcentages dérivés.

    On y ajoute les petits entiers (≤ 12) : « 3 objectifs », « 2 tableaux » sont des dénombrements
    d'objets du texte, pas des données. Un chiffre fabriqué qui compte (« 42 répondants », « 3,7 »,
    « 58 % ») reste détecté.
    """
    allowed: set[str] = {str(r.get("valeur", "")).strip() for r in computed}
    allowed |= derived_percentages(computed)
    for text in sources:
        for token in re.findall(r"\d+(?:[.,]\d+)?", str(text or "")):
            allowed.add(token.strip())
            allowed.add(token.replace(".", ",").strip())
            allowed.add(token.replace(",", ".").strip())
    for number in range(0, 13):
        allowed.add(str(number))
    return {value for value in allowed if value}
