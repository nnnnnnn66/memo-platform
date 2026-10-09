"""Étage de sources déterministe de l'Agent Problématique.

Un seul usage : le « gap check » (SPEC §8, §9.3) — vérifier si la lacune identifiée n'a pas déjà
été comblée par une publication récente. Aucun LLM, aucune clé, aucun coût. Hôtes en liste blanche.
"""

from .cache import GapCheckCache
from .http import ApiFetcher
from .registry import Registry

__all__ = ["ApiFetcher", "GapCheckCache", "Registry"]
