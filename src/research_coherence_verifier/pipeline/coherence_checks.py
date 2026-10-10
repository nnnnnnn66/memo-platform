"""Contrôles de l'audit lui-même (Y1–Y5) : un constat sans preuve, un fait supprimé en silence, une
portée absente ou un verdict hors grille sont refusés AVANT toute remise à l'étudiant.
"""

from ..schemas.audit import Finding, Origine, Severite
from ..schemas.report import verdict_from

#: Constats dont la suppression silencieuse est interdite.
CODES_FAITS = tuple(f"X{i}" for i in range(1, 13))


def run(constats: list[Finding], faits: list[Finding], constats_infirmes: list[Finding],
        non_verifiable: list, verdict) -> list[str]:
    violations: list[str] = []

    # Y1 — aucun constat sans preuve ni sans recommandation.
    for constat in constats:
        if not str(constat.preuve or "").strip():
            violations.append(f"Y1 : le constat « {str(constat.constat)[:70]} » est sans PREUVE. Un "
                              "constat non traçable n'est pas recevable.")
            break
        if not str(constat.recommandation or "").strip():
            violations.append(f"Y1 : le constat « {str(constat.constat)[:70]} » est sans "
                              "recommandation (le rapport doit être actionnable).")
            break

    # Y2 — aucun fait déterministe supprimé en silence.
    if faits:
        codes_faits = {f.code for f in faits if f.code}
        codes_infirmes = {f.code for f in constats_infirmes if f.code}
        codes_retenus = {c.code for c in constats if getattr(c.origine, "value", c.origine)
                         == Origine.deterministe.value}
        perdus = codes_faits - codes_infirmes - codes_retenus
        if perdus:
            violations.append("Y2 : des faits établis par le programme ont disparu sans être infirmés "
                              "ni motivés : " + ", ".join(sorted(perdus)))
        for constat in constats_infirmes:
            if not str(constat.motif_suite or "").strip():
                violations.append("Y2 : un fait a été infirmé sans motif.")
                break

    # Y3 — le verdict correspond à la grille imposée.
    attendu = verdict_from(list(constats))
    if verdict is not None and getattr(verdict, "value", verdict) != attendu.value:
        violations.append(
            f"Y3 : le verdict « {getattr(verdict, 'value', verdict)} » ne correspond pas à la grille "
            f"(constats : bloqueur ⇒ incohérent, majeur ⇒ cohérent avec réserves) — attendu "
            f"« {attendu.value} ».")

    # Y4 — la portée doit être déclarée.
    if not non_verifiable:
        violations.append("Y4 : le rapport ne déclare AUCUN élément non vérifiable. Un audit doit dire "
                          "ce qu'il ne peut pas vérifier.")

    # Y5 — un bloqueur doit être accompagné d'une recommandation de reprise.
    bloqueurs = [c for c in constats if c.severite == Severite.bloqueur]
    if bloqueurs and not any(str(c.recommandation or "").strip() for c in bloqueurs):
        violations.append("Y5 : un constat bloquant sans recommandation de reprise.")
    return violations
