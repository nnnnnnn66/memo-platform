"""Étages déterministes (SPEC §9 étapes 1-2) : état du dossier et FAITS transversaux.

Ces deux étages ne sollicitent AUCUN modèle : ils établissent les faits que le programme peut calculer.
"""

from ..analysis import coherence_rules


def dossier(request):
    """État de complétude du dossier (étapes présentes, vérifiées, éléments de service)."""
    return coherence_rules.etat_du_dossier(request)


def faits(request):
    """FAITS transversaux X1–X12 (constats objectivés, chacun avec sa preuve)."""
    dossier_state, constats = coherence_rules.run_facts(request)
    return dossier_state, constats
