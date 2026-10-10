"""Serveur du site de la plateforme d'accompagnement méthodologique.

Le site affiche et transmet ; il ne décide rien et ne réécrit jamais ce que l'orchestrateur
renvoie. Chaque page vérifie que le mémoire demandé appartient bien au compte connecté.
"""

import hashlib
import hmac
import json
import pathlib
import re
import unicodedata

from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .clients.orchestrateur import ErreurSite, Orchestrateur
from .core import securite
from .core.config import charger
from .storage import comptes

REGLAGES = charger()
ORCHESTRATEUR = Orchestrateur(REGLAGES.orchestrateur_url)
GABARITS = Jinja2Templates(directory=str(REGLAGES.dossier_templates))

# Clé de signature des formulaires : créée une fois, conservée hors du dépôt.
_CLE_CSRF = REGLAGES.base_comptes.parent / ".site-csrf"


def _cle_csrf() -> str:
    if not _CLE_CSRF.exists():
        _CLE_CSRF.parent.mkdir(parents=True, exist_ok=True)
        _CLE_CSRF.write_text(securite.jeton(), encoding="utf-8")
        _CLE_CSRF.chmod(0o600)
    return _CLE_CSRF.read_text(encoding="utf-8").strip()


def jeton_csrf(jeton_session: str) -> str:
    """Jeton de formulaire dérivé de la session : un formulaire d'une autre session est refusé."""
    return hmac.new(_cle_csrf().encode(), jeton_session.encode(), hashlib.sha256).hexdigest()


def csrf_valide(jeton_session: str, fourni: str) -> bool:
    return bool(fourni) and hmac.compare_digest(jeton_csrf(jeton_session), fourni)


# --------------------------------------------------------------------- gabarits
ETIQUETTES = {
    "resume": "Résumé", "analysis": "Analyse du dossier", "diagnosis": "Diagnostic",
    "approche": "Approche", "logique": "Logique de raisonnement", "type_recherche": "Type de recherche",
    "strategie": "Stratégie de recherche", "collecte": "Techniques de collecte",
    "analyse": "Méthodes d'analyse", "articulation": "Articulation des choix",
    "coherence_question": "Réponse à la question", "hypotheses_examined": "Hypothèses examinées",
    "feasibility_controls": "Contrôles de faisabilité", "unknowns": "Ce qui reste inconnu",
    "limits_of_this_output": "Limites", "questions_for_human": "Questions posées",
    "corpus": "Corpus documentaire", "bibliography": "Bibliographie", "synthesis": "Synthèse",
    "comparison": "Mise en regard", "diagnosis_note": "Note de diagnostic",
    "proposition": "Proposition", "justification": "Justification", "alternatives": "Alternatives",
    "conditions": "Conditions", "limites": "Limites", "recommandation": "Recommandation",
    "objectifs": "Objectifs", "objectif_general": "Objectif général",
    "objectifs_specifiques": "Objectifs spécifiques", "hypotheses": "Hypothèses",
    "question": "Question de recherche", "questions_secondaires": "Questions secondaires",
    "problematic": "Problématique", "synthese_pour_conclusion": "Éléments pour la conclusion",
    "protocol": "Protocole", "matrice": "Matrice de cohérence", "versions": "Versions",
}
CLES_TECHNIQUES = {"agent", "version", "doc_id", "provider", "student_id", "session_id",
                   "source_type", "generated_at", "research_id", "status", "at", "code"}


def etiquette(cle: str) -> str:
    if cle in ETIQUETTES:
        return ETIQUETTES[cle]
    return cle.replace("_", " ").strip().capitalize()


# Champs qui servent de TITRE à une fiche (une liste d'objets ne doit jamais produire une
# succession de titres géants : elle produit des fiches lisibles).
CLES_TITRE = ("theme", "titre", "title", "nom", "libelle", "label", "question", "hypothese",
              "objectif", "document", "reference", "reference_courte", "element", "point", "etape")


def titre_element(element):
    """Le meilleur titre disponible pour une fiche — chaîne la plus parlante, sinon rien."""
    if isinstance(element, dict):
        for cle in CLES_TITRE:
            valeur = element.get(cle)
            if isinstance(valeur, str) and valeur.strip():
                return valeur.strip()
        for valeur in element.values():
            if isinstance(valeur, str) and valeur.strip():
                return valeur.strip()
    return ""


def aplatir(valeur):
    """Une liste devient une phrase ; un scalaire reste tel quel."""
    if isinstance(valeur, (list, tuple, set)):
        return " · ".join(str(element) for element in valeur if str(element).strip())
    if isinstance(valeur, dict):
        return " · ".join(f"{cle.replace('_', ' ')} : {val}" for cle, val in valeur.items()
                          if isinstance(val, (str, int, float)) and str(val).strip())
    return valeur


GABARITS.env.filters["etiquette"] = etiquette
GABARITS.env.filters["titre_element"] = titre_element
GABARITS.env.filters["aplatir"] = aplatir
GABARITS.env.globals["CLES_TECHNIQUES"] = CLES_TECHNIQUES


def _slug(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-")[:40] or "memoire"


# ------------------------------------------------------------------------ outil
def _message(type_: str, texte: str) -> dict:
    return {"type": type_, "texte": texte}


def _compte_courant(request: Request):
    jeton = request.cookies.get("session")
    identifiant = comptes.session_valide(REGLAGES.base_comptes, jeton)
    if not identifiant:
        return None, None
    return identifiant, jeton


def _contexte(request: Request, **extra) -> dict:
    identifiant, jeton = _compte_courant(request)
    fiche = comptes.compte(REGLAGES.base_comptes, identifiant) if identifiant else None
    base = {
        "request": request,
        "compte": fiche,
        "admin": bool(fiche and fiche.get("est_admin")),
        "csrf": jeton_csrf(jeton or ""),
        "page": extra.pop("page", ""),
        "message": extra.pop("message", None),
    }
    base.update(extra)
    return base


def _exige_connexion(request: Request):
    identifiant, _ = _compte_courant(request)
    if not identifiant:
        raise _Redirection("/connexion")
    return identifiant


class _Redirection(Exception):
    def __init__(self, cible: str):
        self.cible = cible


app = FastAPI(title="Plateforme d'accompagnement méthodologique")
app.mount("/static", StaticFiles(directory=str(REGLAGES.dossier_static)), name="static")


@app.middleware("http")
async def _en_tetes_protection(request: Request, call_next):
    """Protections appliquées à CHAQUE réponse (OWASP) — jamais laissées au hasard d'une page.

    `script-src 'none'` est tenable parce que le site n'exécute aucun JavaScript : les pages
    sont rendues côté serveur. C'est la meilleure protection contre l'exécution de contenu
    injecté (une sortie d'agent ne peut pas devenir du code)."""
    reponse = await call_next(request)
    reponse.headers["Content-Security-Policy"] = (
        # Les styles en ligne sont tolérés (barre de progression, marges) : un style ne peut pas
        # exécuter de code. Les SCRIPTS, eux, restent totalement interdits ('none').
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "font-src 'self'; script-src 'none'; connect-src 'self'; form-action 'self'; "
        "frame-ancestors 'none'; base-uri 'none'; object-src 'none'")
    reponse.headers["X-Frame-Options"] = "DENY"
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["Referrer-Policy"] = "same-origin"
    reponse.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), usb=()"
    reponse.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    # N'a d'effet qu'en HTTPS (la passerelle) : inoffensif en local.
    reponse.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return reponse


@app.exception_handler(_Redirection)
async def _rediriger(request: Request, erreur: _Redirection):
    return RedirectResponse(erreur.cible, status_code=303)


@app.exception_handler(ErreurSite)
async def _erreur_site(request: Request, erreur: ErreurSite):
    return GABARITS.TemplateResponse(
        request, "erreur.html", _contexte(request, message=_message("erreur", erreur.message)),
        status_code=200)


# -------------------------------------------------------------------- connexion
@app.get("/", response_class=HTMLResponse)
async def racine(request: Request):
    identifiant, _ = _compte_courant(request)
    return RedirectResponse("/mes-memoires" if identifiant else "/connexion", status_code=303)


@app.get("/connexion", response_class=HTMLResponse)
async def page_connexion(request: Request, message: str = ""):
    return GABARITS.TemplateResponse(
        request, "connexion.html", _contexte(
        request, page="connexion",
        message=_message("erreur", message) if message else None,
        premiere_visite=False, identifiant=""))


@app.get("/invitation/{jeton}", response_class=HTMLResponse)
async def page_invitation(request: Request, jeton: str):
    if not comptes.invitation_valide(REGLAGES.base_comptes, jeton):
        return RedirectResponse("/connexion?message=" + "Cette invitation n'est plus valable.",
                                status_code=303)
    return GABARITS.TemplateResponse(
        request, "connexion.html", _contexte(
        request, page="connexion", premiere_visite=True, jeton_invitation=jeton))


@app.post("/activer")
async def activer(request: Request, mot_de_passe: str = Form(""), confirmation: str = Form(""),
                  csrf: str = Form(""), jeton: str = Form("")):
    if not csrf_valide(request.cookies.get("session", ""), csrf):
        return RedirectResponse("/connexion?message=L'envoi du formulaire a échoué. Réessayez.",
                                status_code=303)
    if not comptes.invitation_valide(REGLAGES.base_comptes, jeton):
        return RedirectResponse("/connexion?message=Cette invitation n'est plus valable.",
                                status_code=303)
    if mot_de_passe != confirmation:
        return RedirectResponse(f"/invitation/{jeton}?message=Les deux mots de passe diffèrent.",
                                status_code=303)
    valide, explication = securite.mot_de_passe_valide(mot_de_passe)
    if not valide:
        return RedirectResponse(f"/invitation/{jeton}?message={explication}", status_code=303)

    identifiant = "etudiant-" + jeton[:8]
    comptes.creer_compte(REGLAGES.base_comptes, identifiant, securite.hacher(mot_de_passe))
    comptes.consommer_invitation(REGLAGES.base_comptes, jeton)
    comptes.consigner(REGLAGES.base_comptes, "compte créé", identifiant)
    jeton_session = comptes.ouvrir_session(REGLAGES.base_comptes, identifiant,
                                           REGLAGES.duree_session_heures)
    reponse = RedirectResponse("/mes-memoires", status_code=303)
    reponse.set_cookie("session", jeton_session, httponly=True, samesite="lax",
                       max_age=REGLAGES.duree_session_heures * 3600)
    return reponse


@app.post("/connexion")
async def connexion(request: Request, identifiant: str = Form(""), mot_de_passe: str = Form(""),
                    csrf: str = Form("")):
    if not csrf_valide(request.cookies.get("session", ""), csrf):
        return RedirectResponse("/connexion?message=L'envoi du formulaire a échoué. Réessayez.",
                                status_code=303)
    identifiant = identifiant.strip().lower()
    if comptes.est_bloque(REGLAGES.base_comptes, identifiant):
        return RedirectResponse("/connexion?message=Accès temporairement bloqué après plusieurs "
                                "tentatives. Réessayez dans quelques minutes.", status_code=303)

    empreinte = comptes.empreinte_de(REGLAGES.base_comptes, identifiant)
    if not empreinte or not securite.verifier(mot_de_passe, empreinte):
        comptes.enregistrer_echec(REGLAGES.base_comptes, identifiant,
                                  REGLAGES.max_tentatives, REGLAGES.blocage_minutes)
        # Message VOLONTAIREMENT identique dans les deux cas : il ne révèle pas si le compte existe.
        return RedirectResponse("/connexion?message=Identifiant ou mot de passe incorrect.",
                                status_code=303)

    comptes.reinitialiser_tentatives(REGLAGES.base_comptes, identifiant)
    comptes.consigner(REGLAGES.base_comptes, "connexion", identifiant)
    jeton_session = comptes.ouvrir_session(REGLAGES.base_comptes, identifiant,
                                           REGLAGES.duree_session_heures)
    reponse = RedirectResponse("/mes-memoires", status_code=303)
    reponse.set_cookie("session", jeton_session, httponly=True, samesite="lax",
                       max_age=REGLAGES.duree_session_heures * 3600)
    return reponse


@app.get("/deconnexion")
async def deconnexion(request: Request):
    comptes.fermer_session(REGLAGES.base_comptes, request.cookies.get("session", ""))
    reponse = RedirectResponse("/connexion", status_code=303)
    reponse.delete_cookie("session")
    return reponse


# --------------------------------------------------------------------- mémoires
@app.get("/mes-memoires", response_class=HTMLResponse)
async def page_mes_memoires(request: Request, message: str = ""):
    identifiant = _exige_connexion(request)
    memoires = []
    for memoire in comptes.mes_memoires(REGLAGES.base_comptes, identifiant):
        etat = ORCHESTRATEUR.dossier(identifiant, memoire["session"])
        validees = sum(1 for e in etat.get("avancement", []) if e.get("statut") == "validee")
        memoires.append({**memoire, "faites": validees, "libelle": etat.get("libelle", "")})
    return GABARITS.TemplateResponse(
        request, "mes_memoires.html", _contexte(
        request, page="memoires", memoires=memoires, formulaire={},
        message=_message("erreur", message) if message else None))


@app.post("/mes-memoires")
async def creer_memoire(request: Request, sujet: str = Form(""), discipline: str = Form(""),
                        country: str = Form(""), geographical_scope: str = Form(""),
                        period: str = Form(""), research_problem: str = Form(""),
                        csrf: str = Form("")):
    identifiant = _exige_connexion(request)
    if not csrf_valide(request.cookies.get("session", ""), csrf):
        return RedirectResponse("/mes-memoires?message=L'envoi du formulaire a échoué.",
                                status_code=303)
    sujet = sujet.strip()
    if len(sujet) < 8:
        return RedirectResponse("/mes-memoires?message=Décrivez votre sujet en quelques mots.",
                                status_code=303)

    session = _slug(sujet)
    complet = session
    rang = 2
    while comptes.mon_memoire(REGLAGES.base_comptes, identifiant, complet):
        complet = f"{session}-{rang}"
        rang += 1

    contexte = {"discipline": discipline.strip(), "country": country.strip(),
                "geographical_scope": geographical_scope.strip(), "period": period.strip(),
                "research_problem": research_problem.strip()}
    contexte = {cle: valeur for cle, valeur in contexte.items() if valeur}
    ORCHESTRATEUR.creer_dossier(identifiant, complet, sujet, contexte)
    comptes.creer_memoire(REGLAGES.base_comptes, identifiant, complet, sujet,
                          json.dumps(contexte, ensure_ascii=False))
    comptes.consigner(REGLAGES.base_comptes, "mémoire créé", identifiant, complet, sujet[:120])
    return RedirectResponse(f"/memoire/{complet}", status_code=303)


def _memoire_autorise(request: Request, session: str) -> tuple:
    identifiant = _exige_connexion(request)
    memoire = comptes.mon_memoire(REGLAGES.base_comptes, identifiant, session)
    if not memoire:
        raise _Redirection("/mes-memoires")
    return identifiant, memoire


# ---------------------------------------------------------------------- parcours
@app.get("/memoire/{session}", response_class=HTMLResponse)
async def page_parcours(request: Request, session: str, message: str = ""):
    identifiant, memoire = _memoire_autorise(request, session)
    etat = ORCHESTRATEUR.dossier(identifiant, session)
    etapes = _etapes_affichees(etat)
    faites = sum(1 for e in etapes if e["statut"] == "validee")
    return GABARITS.TemplateResponse(
        request, "parcours.html", _contexte(
        request, page="parcours", memoire={**memoire, "libelle": etat.get("libelle", "")},
        etapes=etapes,
        memoires_avancement={"faites": faites, "total": len(etapes),
                             "pourcent": round(100 * faites / max(1, len(etapes)))},
        quota={"restant": etat.get("quota_restant", 0), "max": etat.get("quota_max", 0)},
        message=_message("erreur", message) if message else None))


def _etapes_affichees(etat: dict) -> list:
    """Construit la liste des étapes à afficher depuis l'état renvoyé par l'orchestrateur."""
    avancement = {e["numero"]: e for e in etat.get("avancement", [])}
    ouverte = etat.get("etape_ouverte")
    lignes = []
    for definition in etat.get("etapes", []):
        numero = definition["numero"]
        fiche = avancement.get(numero, {})
        statut = fiche.get("statut", "a_faire")
        fermee = numero > (ouverte or 0) and statut == "a_faire"
        etiquette_texte, classe = {
            "validee": ("validée", "validee"),
            "proposee": ("en attente de votre décision", "attente"),
            "a_reviser": ("à réviser", "a-reviser"),
            "echec": ("en échec", "echec"),
        }.get(statut, ("fermée" if fermee else "à faire", "a-faire"))
        libelle_note = {
            "validee": "Étape validée",
            "proposee": "Proposition en attente de votre lecture",
            "a_reviser": "Révision demandée : l'étape reste ouverte",
            "echec": "L'étape n'a pas abouti — vous pouvez la relancer",
        }.get(statut)
        if libelle_note is None:
            libelle_note = ("Disponible après les étapes précédentes" if fermee
                            else "Prête à être lancée")
        lignes.append({
            "numero": numero,
            "libelle": definition["libelle"],
            "statut": statut if not fermee else "fermee",
            "ouverte": numero == ouverte,
            "etiquette": etiquette_texte,
            "classe": classe,
            "note": libelle_note,
        })
    return lignes


@app.post("/memoire/{session}/etape/lancer")
async def lancer_etape(request: Request, session: str, csrf: str = Form("")):
    identifiant, _ = _memoire_autorise(request, session)
    if not csrf_valide(request.cookies.get("session", ""), csrf):
        return RedirectResponse(f"/memoire/{session}?message=L'envoi du formulaire a échoué.",
                                status_code=303)
    resultat = ORCHESTRATEUR.lancer_etape(identifiant, session)
    comptes.consigner(REGLAGES.base_comptes, "étape lancée", identifiant, session,
                      f"étape {resultat.get('etape')} — {resultat.get('verdict', '')}")
    return RedirectResponse(f"/memoire/{session}/etape", status_code=303)


@app.get("/memoire/{session}/etape", response_class=HTMLResponse)
async def page_etape(request: Request, session: str, n: int = 0, message: str = ""):
    identifiant, memoire = _memoire_autorise(request, session)
    detail = ORCHESTRATEUR.etape(identifiant, session, n or None)
    return GABARITS.TemplateResponse(
        request, "etape.html", _contexte(
        request, page="parcours", memoire=memoire,
        etape={"numero": detail["numero"], "libelle": detail["libelle"],
               "statut": detail["statut"], "ouverte": detail.get("ouverte", False)},
        proposition=detail.get("resultat"),
        inconnues=detail.get("inconnues", []),
        limites=detail.get("limites", []),
        questions=detail.get("questions", []),
        signalements=detail.get("signalements", []),
        verdict=detail.get("verdict", ""), verdict_texte=detail.get("verdict_texte", ""),
        message=_message("erreur", message) if message else None))


@app.post("/memoire/{session}/etape/decision")
async def decider(request: Request, session: str, csrf: str = Form(""),
                  decision: str = Form("accepted"), commentaire: str = Form("")):
    identifiant, _ = _memoire_autorise(request, session)
    if not csrf_valide(request.cookies.get("session", ""), csrf):
        return RedirectResponse(f"/memoire/{session}/etape?message=L'envoi du formulaire a échoué.",
                                status_code=303)
    resultat = ORCHESTRATEUR.decider(identifiant, session, decision, commentaire)
    comptes.consigner(REGLAGES.base_comptes, "décision",
                      identifiant, session,
                      f"étape {resultat.get('etape')} : {'validée' if decision == 'accepted' else 'à réviser'}")
    if decision == "accepted":
        return RedirectResponse(f"/memoire/{session}", status_code=303)
    return RedirectResponse(f"/memoire/{session}/etape", status_code=303)


# ------------------------------------------------------------ documents & export
@app.get("/memoire/{session}/documents", response_class=HTMLResponse)
async def page_documents(request: Request, session: str):
    identifiant, memoire = _memoire_autorise(request, session)
    manifeste = ORCHESTRATEUR.documents(identifiant, session)
    return GABARITS.TemplateResponse(
        request, "documents.html", _contexte(
        request, page="parcours", memoire=memoire,
        documents=manifeste.get("entries", []), resume=manifeste.get("resume", {})))


@app.get("/memoire/{session}/documents/{doc_id}/fichier")
async def telecharger_document(request: Request, session: str, doc_id: str):
    identifiant, _ = _memoire_autorise(request, session)
    contenu = ORCHESTRATEUR.fichier_document(identifiant, session, doc_id)
    return Response(content=contenu, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{_slug(doc_id)}.pdf"'})


@app.get("/memoire/{session}/bibliographie")
async def telecharger_bibliographie(request: Request, session: str, format: str = "bibtex"):
    identifiant, _ = _memoire_autorise(request, session)
    contenu = ORCHESTRATEUR.bibliographie(identifiant, session, format)
    extensions = {"bibtex": "bib", "ris": "ris", "csv": "csv"}
    types = {"bibtex": "application/x-bibtex", "ris": "application/x-research-info-systems",
             "csv": "text/csv"}
    return Response(content=contenu, media_type=types.get(format, "application/octet-stream"),
                    headers={"Content-Disposition":
                             f'attachment; filename="bibliographie.{extensions.get(format, "txt")}"'})


@app.get("/memoire/{session}/journal", response_class=HTMLResponse)
async def page_journal(request: Request, session: str):
    identifiant, memoire = _memoire_autorise(request, session)
    etat = ORCHESTRATEUR.dossier(identifiant, session)
    return GABARITS.TemplateResponse(
        request, "journal.html", _contexte(
        request, page="parcours", memoire=memoire,
        avancement=etat.get("avancement", []),
        evenements=comptes.journal(REGLAGES.base_comptes, identifiant, 40)))


@app.get("/memoire/{session}/export")
async def exporter(request: Request, session: str):
    identifiant, memoire = _memoire_autorise(request, session)
    etat = ORCHESTRATEUR.dossier(identifiant, session)
    comptes.consigner(REGLAGES.base_comptes, "export du dossier", identifiant, session)
    contenu = json.dumps({"memoire": memoire, "etat": etat}, ensure_ascii=False, indent=2)
    return Response(content=contenu, media_type="application/json",
                    headers={"Content-Disposition":
                             f'attachment; filename="{session}-dossier.json"'})


# -------------------------------------------------------------- tableau de bord
@app.get("/tableau-de-bord", response_class=HTMLResponse)
async def page_tableau(request: Request):
    identifiant, _ = _compte_courant(request)
    if not identifiant:
        return RedirectResponse("/connexion", status_code=303)
    fiche = comptes.compte(REGLAGES.base_comptes, identifiant)
    if not fiche or not fiche.get("est_admin"):
        return RedirectResponse("/mes-memoires", status_code=303)
    return GABARITS.TemplateResponse(
        request, "tableau_de_bord.html", _contexte(
        request, page="admin", agents=ORCHESTRATEUR.agents(),
        invitations=comptes.invitations_ouvertes(REGLAGES.base_comptes),
        evenements=comptes.journal(REGLAGES.base_comptes, "", 40),
        comptes_total=comptes.nombre_comptes(REGLAGES.base_comptes)))


@app.post("/tableau-de-bord/invitation")
async def creer_invitation(request: Request, email: str = Form(""), csrf: str = Form("")):
    identifiant, _ = _compte_courant(request)
    fiche = comptes.compte(REGLAGES.base_comptes, identifiant) if identifiant else None
    if not fiche or not fiche.get("est_admin"):
        return RedirectResponse("/mes-memoires", status_code=303)
    if not csrf_valide(request.cookies.get("session", ""), csrf):
        return RedirectResponse("/tableau-de-bord", status_code=303)
    jeton = securite.jeton()
    comptes.creer_invitation(REGLAGES.base_comptes, jeton, email.strip())
    comptes.consigner(REGLAGES.base_comptes, "invitation créée", identifiant, "", email)
    return RedirectResponse("/tableau-de-bord", status_code=303)
