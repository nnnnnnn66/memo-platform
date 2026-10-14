"""Preuve HTTP RÉELLE de « reprendre une étape déjà franchie » (instance isolée sur 8001).

L'orchestrateur de production (8000) tourne depuis avant la modification : c'est ce même code,
la même carte, les mêmes agents et le même dossier, mais une instance isolée sur 8001 avec un
état SQLite COPIE — pour ne pas muter l'état partagé de la plateforme.
"""
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8001"
E = "etudiant-demo"
S = "promotions-immobilieres-bingerville-v2"


def appel(methode, chemin, corps=None):
    data = json.dumps(corps).encode() if corps is not None else None
    requete = urllib.request.Request(BASE + chemin, data=data, method=methode,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(requete, timeout=120) as reponse:
            return reponse.status, json.loads(reponse.read() or b"{}")
    except urllib.error.HTTPError as erreur:
        return erreur.code, json.loads(erreur.read() or b"{}")


def resume(etat):
    return " | ".join(f"{l['numero']}:{l['statut']}/{l['verdict']}"
                      for l in etat["avancement"])


print("=" * 78)
print("AVANT")
print("=" * 78)
code, etat = appel("GET", f"/dossiers/{E}/{S}")
print("GET dossier ->", code, "| étape ouverte =", etat["etape_ouverte"],
      etat["libelle"], "| quota =", etat["quota_restant"])
print(resume(etat))
code, d9 = appel("GET", f"/dossiers/{E}/{S}/etape?n=9")
print("étape 9 :", code, {k: d9[k] for k in ("statut", "verdict", "reprises", "repose_sur")})

print()
print("=" * 78)
print("REPRISE DE L'ÉTAPE 9 (Méthodologie — franchie et vérifiée)")
print("=" * 78)
code, corps = appel("POST", f"/dossiers/{E}/{S}/etapes/9/reprendre")
print("POST .../etapes/9/reprendre ->", code)
print(json.dumps(corps, ensure_ascii=False, indent=2))

print()
print("--- APRÈS la reprise : état du dossier ---")
code, etat = appel("GET", f"/dossiers/{E}/{S}")
print("GET dossier ->", code, "| étape ouverte =", etat["etape_ouverte"],
      etat["libelle"], "| quota =", etat["quota_restant"])
print(resume(etat))
for n in (9, 10, 13, 11):
    code, d = appel("GET", f"/dossiers/{E}/{S}/etape?n={n}")
    print(f"  étape {n:>2} -> HTTP {code} | statut={d['statut']:<9} a_venir={d['a_venir']} "
          f"reprises={d['reprises']} repose_sur={d['repose_sur']}")
    if d["historique_reprises"]:
        h = d["historique_reprises"][0]
        print(f"           journal : ancien_statut={h['ancien_statut']} "
              f"ancien_verdict={h['ancien_verdict']} ancienne_decision={h['ancienne_decision']} "
              f"aval={h['aval']}")

print()
print("=" * 78)
print("REFUS (les règles tiennent)")
print("=" * 78)
code, corps = appel("POST", f"/dossiers/{E}/{S}/etapes/11/reprendre")
print(f"étape 11 (proposée, pas franchie) -> HTTP {code} | {corps['detail']['error']} "
      f"| {corps['detail']['message']}")
code, corps = appel("POST", f"/dossiers/{E}/{S}/etapes/12/reprendre")
print(f"étape 12 (hors parcours)          -> HTTP {code} | {corps['detail']['error']}")
code, corps = appel("POST", "/dossiers/personne/inconnu/etapes/1/reprendre")
print(f"dossier inconnu                   -> HTTP {code} | {corps['detail']['error']}")

temoin = "temoin-reprise"
appel("POST", f"/dossiers/{temoin}/s1", {"sujet": "Le télétravail et la productivité"})
code, corps = appel("POST", f"/dossiers/{temoin}/s1/etapes/5/reprendre")
print(f"étape JAMAIS atteinte (dossier neuf) -> HTTP {code} | {corps['detail']['error']} "
      f"| {corps['detail']['message']}")
code, etat_temoin = appel("GET", f"/dossiers/{temoin}/s1")
print(f"   dossier témoin inchangé : étape ouverte = {etat_temoin['etape_ouverte']}")
