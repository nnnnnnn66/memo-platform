"""Auto-héberge les polices du site : deux familles, téléchargées UNE fois, servies en local.

Pourquoi : un site beau a besoin d'une vraie typographie, mais le site ne doit dépendre d'AUCUN
CDN (fonctionne hors ligne, respecte une CSP stricte, et n'envoie pas ses visiteurs chez un tiers).
On télécharge donc les fichiers woff2 du sous-ensemble latin et on écrit nos propres règles
`@font-face` pointant vers `static/fonts/`.

Usage :  .venv/bin/python scripts/installer_polices.py
"""

import pathlib
import re
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120 Safari/537.36")
SORTIE = pathlib.Path(__file__).resolve().parents[1] / "src" / "site_web" / "static" / "fonts"

FAMILLES = {
    "Fraunces": "Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700",
    "InterTight": "Inter+Tight:wght@400;500;600",
}
# Sous-ensembles conservés : le latin couvre le français ; on garde `latin-ext` pour les noms
# propres (africains, européens) qui débordent parfois du latin de base.
GARDES = ("latin", "latin-ext")


def css_google(specification: str) -> str:
    url = f"https://fonts.googleapis.com/css2?family={specification}&display=swap"
    requete = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        return reponse.read().decode("utf-8")


def blocs(css: str):
    """Découpe le CSS de Google en (sous-ensemble, contenu du bloc @font-face)."""
    morceaux = re.split(r"/\*\s*([a-z0-9\-]+)\s*\*/", css)
    for indice in range(1, len(morceaux) - 1, 2):
        yield morceaux[indice], morceaux[indice + 1]


def main() -> int:
    SORTIE.mkdir(parents=True, exist_ok=True)
    regles: list[str] = []
    telecharges = 0
    for famille, specification in FAMILLES.items():
        css = css_google(specification)
        vus: set = set()
        for sous_ensemble, bloc in blocs(css):
            if sous_ensemble not in GARDES:
                continue
            url = re.search(r"url\((https://[^)]+\.woff2)\)", bloc)
            poids = re.search(r"font-weight:\s*([0-9]+)", bloc)
            if not url or not poids:
                continue
            cle = (poids.group(1), sous_ensemble)
            if cle in vus:
                continue
            vus.add(cle)
            nom_fichier = f"{famille}-{poids.group(1)}-{sous_ensemble}.woff2"
            destination = SORTIE / nom_fichier
            if not destination.exists():
                requete = urllib.request.Request(url.group(1), headers={"User-Agent": UA})
                with urllib.request.urlopen(requete, timeout=30) as reponse:
                    destination.write_bytes(reponse.read())
                telecharges += 1
            regles.append(
                "@font-face {\n"
                f"  font-family: '{famille}';\n"
                "  font-style: normal;\n"
                f"  font-weight: {poids.group(1)};\n"
                "  font-display: swap;\n"
                f"  src: url('fonts/{nom_fichier}') format('woff2');\n"
                "}")
    (SORTIE.parent / "polices.css").write_text("\n\n".join(regles) + "\n", encoding="utf-8")
    print(f"  {len(regles)} règles @font-face écrites, {telecharges} fichier(s) téléchargé(s)")
    for fichier in sorted(SORTIE.glob("*.woff2")):
        print(f"    {fichier.name}  ({fichier.stat().st_size // 1024} ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
