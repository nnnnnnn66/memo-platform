"""Test de CHAÎNE RÉEL : Agent 1 → 2 → 3 → 4 → 5, sur sorties RÉELLES.

Chaque agent reçoit la sortie RÉELLE du précédent (jamais un payload fabriqué — c'est la leçon
d'un bug antérieur : la sortie de l'agent 3 place ses documents sous `corpus.documents` et l'entrée
de l'agent 4 les attendait à la racine, ce qu'aucun test à payload manuel n'avait vu).

Usage :
    set -a; . ~/.hermes/.env; set +a
    PYTHONPATH=src .venv/bin/python scripts/e2e_chaine.py [depuis=1]

`depuis=N` reprend à l'étape N (les sorties des étapes précédentes sont relues depuis le disque) —
utile car l'étape 3 interroge le réseau et lit des PDF (10 à 25 min).
Chaque étape est écrite dans `workspace/chaine-live/stageN.json`.
"""

import json
import pathlib
import sys
import time

ROOT = pathlib.Path("/root/memo-platform")
sys.path.insert(0, str(ROOT / "src"))

STUDENT = "chaine-etu"
SESSION = "chaine-live"
OUT = ROOT / "workspace" / "chaine-live"
OUT.mkdir(parents=True, exist_ok=True)

SUJET = "Effets du télétravail sur la productivité des développeurs d'Abidjan, 2020-2024"
PROBLEME = ("Les entreprises de services numériques d'Abidjan constatent, depuis le passage au "
            "télétravail en 2020, une dégradation de la tenue des délais et une coordination "
            "affaiblie entre développeurs, sans savoir si ces effets viennent du télétravail.")
OBSERVATIONS = ("Des équipes de développement peinent à tenir leurs délais ; le turnover des "
                "développeurs a augmenté depuis 2020.")
DEPENDANCES_ETUDIANT = ("Mémoire de Master 2, six mois de terrain, budget limité ; accès aux "
                       "entreprises par un réseau professionnel.")

#: Jeu de données FOURNI par l'« étudiant » du test (données d'enquête brutes). C'est une ENTRÉE du
#: système, jamais une sortie d'agent : l'agent 10 n'en invente aucune valeur, il la CALCULE.
DATASET_ETUDIANT = """repondant,ville,jours_teletravail,coordination,productivite_declaree
D01,Abidjan,3,4,7
D02,Abidjan,1,3,5
D03,Bouaké,0,3,6
D04,Abidjan,4,5,8
D05,Bouaké,,2,5
D06,Abidjan,2,4,6
D07,Abidjan,5,5,8
D08,Bouaké,1,2,4
D09,Abidjan,3,4,7
D10,Abidjan,0,3,5
D11,Bouaké,2,3,6
D12,Abidjan,4,5,8
D13,Abidjan,1,2,4
D14,Bouaké,3,4,7
D15,Abidjan,2,3,6
D16,Abidjan,4,4,7
D17,Bouaké,0,2,4
D18,Abidjan,3,5,8
D19,Abidjan,2,3,5
D20,Bouaké,1,3,6
"""

START = int(sys.argv[1].split("=")[1]) if len(sys.argv) > 1 and "=" in sys.argv[1] else 1


def save(stage: int, obj: dict) -> None:
    path = OUT / f"stage{stage}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def load(stage: int) -> dict:
    return json.loads((OUT / f"stage{stage}.json").read_text(encoding="utf-8"))


def banner(text: str) -> None:
    print("\n" + "=" * 78)
    print(text)
    print("=" * 78, flush=True)


def main() -> int:
    results: dict[int, dict] = {}

    # ---------------- ÉTAPE 1 : Agent Sujet ----------------
    if START <= 1:
        banner("[1/8] Agent Sujet — modèle réel")
        from subject_agent.core.config import get_settings as settings1
        from subject_agent.llm.client import LLMClient as Client1
        from subject_agent.pipeline import input_controller as ic1, orchestrator as o1
        from subject_agent.schemas.input import SubjectRequest

        s = settings1()
        llm = Client1(s.llm_credentials(), s.limits)
        body = SubjectRequest(student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
                              discipline="Sciences de gestion", academic_level="Master 2",
                              country="Côte d'Ivoire")
        res = o1.analyze_subject(ic1.prepare(body), s, llm)
        results[1] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": llm.calls}
        save(1, results[1])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("appels LLM       :", llm.calls, flush=True)
        if res.verifier_status != "verified":
            print(">>> ARRÊT : l'agent 1 n'est pas vérifié.", flush=True)
            return 1
    else:
        results[1] = load(1)
        print("[1/8] reprise : sortie de l'agent 1 relue depuis le disque", flush=True)

    # ---------------- ÉTAPE 2 : Agent Problème ----------------
    if START <= 2:
        banner("[2/8] Agent Problème — modèle réel + recherche réseau réelle")
        from research_problem_agent.core.config import get_settings as settings2
        from research_problem_agent.llm.client import LLMClient as Client2
        from research_problem_agent.pipeline import input_controller as ic2, orchestrator as o2
        from research_problem_agent.schemas.input import ProblemRequest as Request2

        s = settings2()
        llm = Client2(s.llm_credentials(), s.limits)
        body = Request2(student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
                        observations=OBSERVATIONS, discipline="Sciences de gestion",
                        academic_level="Master 2", country="Côte d'Ivoire",
                        upstream_subject=results[1]["output"])
        res = o2.analyze_problem(ic2.prepare(body), s, llm)
        results[2] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": llm.calls,
                      "external_requests": res.external_requests,
                      "providers_used": res.source_set.providers_used if res.source_set else []}
        save(2, results[2])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("fournisseurs     :", results[2]["providers_used"])
        print("appels LLM       :", llm.calls, "| requêtes réseau :", res.external_requests,
              flush=True)
        if res.verifier_status != "verified":
            print(">>> ARRÊT : l'agent 2 n'est pas vérifié.", flush=True)
            return 2
    else:
        results[2] = load(2)
        print("[2/8] reprise : sortie de l'agent 2 relue depuis le disque", flush=True)

    # ---------------- ÉTAPE 3 : Agent Revue de littérature ----------------
    if START <= 3:
        banner("[3/8] Agent Revue de littérature — réseau réel + PDF réels (patience : 10-25 min)")
        from literature_review_agent.core.config import get_settings as settings3
        from literature_review_agent.llm.client import LLMClient as Client3
        from literature_review_agent.pipeline import campaign as campaign3
        from literature_review_agent.schemas.input import CampaignRequest

        s = settings3()
        llm = Client3(s.llm_credentials(), s.limits)
        body = CampaignRequest(student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
                               research_problem=PROBLEME, discipline="Sciences de gestion",
                               academic_level="Master 2", country="Côte d'Ivoire",
                               geographical_scope="Abidjan", period="2020-2024",
                               upstream_subject=results[1]["output"],
                               upstream_problem=results[2]["output"])
        t0 = time.time()
        res = campaign3.run(body, s, llm)
        results[3] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": llm.calls,
                      "verifier": res.verifier.model_dump(mode="json") if res.verifier else None,
                      "seconds": round(time.time() - t0)}
        save(3, results[3])
        docs = (results[3]["output"].get("corpus") or {}).get("documents") or []
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("documents        :", len(docs), "| dont texte intégral :",
              sum(1 for d in docs if (d.get("full_text") or {}).get("downloaded")))
        print("appels LLM       :", llm.calls, "| durée :", results[3]["seconds"], "s", flush=True)
        if res.verifier_status != "verified":
            print(">>> ARRÊT : l'agent 3 n'est pas vérifié.", flush=True)
            return 3
    else:
        results[3] = load(3)
        print("[3/8] reprise : sortie de l'agent 3 relue depuis le disque", flush=True)

    # ---------------- ÉTAPE 4 : Agent Problématique ----------------
    if START <= 4:
        banner("[4/8] Agent Problématique — modèle réel + gap check réseau")
        from problematization_agent.core.config import get_settings as settings4
        from problematization_agent.llm.client import LLMClient as Client4
        from problematization_agent.pipeline import campaign as campaign4
        from problematization_agent.schemas.input import ProblemRequest as Request4

        s = settings4()
        llm = Client4(s.llm_credentials(), s.limits)
        # Les textes intégralement lus par l'agent 3 sont sous workspace/<étudiant>/<session>/documents/
        documents_dir = ROOT / "workspace" / STUDENT / SESSION / "documents"
        body = Request4(student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
                        research_problem=PROBLEME, discipline="Sciences de gestion",
                        academic_level="Master 2", country="Côte d'Ivoire",
                        geographical_scope="Abidjan", period="2020-2024",
                        population="développeurs", field_observations=OBSERVATIONS,
                        upstream_subject=results[1]["output"],
                        upstream_problem=results[2]["output"],
                        upstream_literature=results[3]["output"],
                        documents_dir=str(documents_dir))
        res = campaign4.run(body, s, llm, allow_network=True)
        results[4] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                      "verifier": res.verifier.model_dump(mode="json") if res.verifier else None,
                      "external_requests": res.external_requests}
        save(4, results[4])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("appels LLM       :", res.llm_calls, "| requêtes réseau :", res.external_requests,
              flush=True)
        if res.verifier_status != "verified":
            print(">>> ARRÊT : l'agent 4 n'est pas vérifié.", flush=True)
            return 4
    else:
        results[4] = load(4)
        print("[4/8] reprise : sortie de l'agent 4 relue depuis le disque", flush=True)

    # ---------------- ÉTAPE 5 : Agent Question de recherche ----------------
    if START <= 5:
        banner("[5/8] Agent Question de recherche — modèle réel")
        from research_question_agent.core.config import get_settings as settings5
        from research_question_agent.llm.client import LLMClient as Client5
        from research_question_agent.pipeline import campaign as campaign5
        from research_question_agent.schemas.input import QuestionRequest

        s = settings5()
        llm = Client5(s.llm_credentials(), s.limits)
        body = QuestionRequest(student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
                               discipline="Sciences de gestion", academic_level="Master 2",
                               country="Côte d'Ivoire", geographical_area="Abidjan",
                               study_period="2020-2024", target_population="développeurs",
                               upstream_subject=results[1]["output"],
                               upstream_problem=results[2]["output"],
                               upstream_problematic=results[4]["output"])
        res = campaign5.run(body, s, llm, allow_network=False)
        results[5] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": res.llm_calls}
        save(5, results[5])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("question         :", res.output.main_research_question)
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[5] = load(5)
        print("[5/8] reprise : sortie de l'agent 5 relue depuis le disque", flush=True)
    if results[5].get("verifier_status") != "verified":
        print(">>> ARRÊT : l'agent 5 n'est pas vérifié.", flush=True)
        return 5

    # ---------------- ÉTAPE 6 : Agent Objectifs de recherche ----------------
    if START <= 6:
        banner("[6/8] Agent Objectifs de recherche — modèle réel")
        from research_objectives_agent.core.config import get_settings as settings6
        from research_objectives_agent.llm.client import LLMClient as Client6
        from research_objectives_agent.pipeline import campaign as campaign6
        from research_objectives_agent.schemas.input import ObjectivesRequest

        s = settings6()
        llm = Client6(s.llm_credentials(), s.limits)
        body = ObjectivesRequest(
            student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
            validated_problematic=results[4]["output"].get("problematique_note", {}).get(
                "texte_complet", PROBLEME),
            main_research_question=results[5]["output"].get("main_research_question"),
            secondary_research_questions=results[5]["output"].get(
                "secondary_research_questions") or [],
            discipline="Sciences de gestion", academic_level="Master 2",
            country="Côte d'Ivoire", geographical_area="Abidjan", study_period="2020-2024",
            target_population="développeurs",
            upstream_subject=results[1]["output"], upstream_problem=results[2]["output"],
            upstream_problematic=results[4]["output"], upstream_question=results[5]["output"])
        res = campaign6.run(body, s, llm, allow_network=True)
        results[6] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                      "verifier": res.verifier.model_dump(mode="json") if res.verifier else None}
        save(6, results[6])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("objectif général :", (res.output.general_objective or "")[:120])
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[6] = load(6)
        print("[6/8] reprise : sortie de l'agent 6 relue depuis le disque", flush=True)
    if results[6].get("verifier_status") != "verified":
        print(">>> ARRÊT : l'agent 6 n'est pas vérifié.", flush=True)
        return 6

    # ---------------- ÉTAPE 7 : Agent Hypothèses de recherche ----------------
    if START <= 7:
        banner("[7/8] Agent Hypothèses de recherche — modèle réel")
        from research_hypotheses_agent.core.config import get_settings as settings7
        from research_hypotheses_agent.llm.client import LLMClient as Client7
        from research_hypotheses_agent.pipeline import campaign as campaign7
        from research_hypotheses_agent.schemas.input import HypothesesRequest

        s = settings7()
        llm = Client7(s.llm_credentials(), s.limits)
        body = HypothesesRequest(
            student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
            main_research_question=results[5]["output"].get("main_research_question"),
            secondary_research_questions=results[5]["output"].get(
                "secondary_research_questions") or [],
            general_objective=results[6]["output"].get("general_objective"),
            specific_objectives=results[6]["output"].get("specific_objectives") or [],
            discipline="Sciences de gestion", academic_level="Master 2",
            country="Côte d'Ivoire", geographical_area="Abidjan", study_period="2020-2024",
            target_population="développeurs",
            upstream_subject=results[1]["output"], upstream_problem=results[2]["output"],
            upstream_problematic=results[4]["output"], upstream_question=results[5]["output"],
            upstream_objectives=results[6]["output"])
        res = campaign7.run(body, s, llm, allow_network=True)
        results[7] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                      "verifier": res.verifier.model_dump(mode="json") if res.verifier else None}
        save(7, results[7])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("décision         :", getattr(res.output.hypotheses_decision, "value",
                                          res.output.hypotheses_decision))
        print("hypothèses       :", len(res.output.research_hypotheses or []))
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[7] = load(7)
        print("[7/8] reprise : sortie de l'agent 7 relue depuis le disque", flush=True)
    if results[7].get("verifier_status") != "verified":
        print(">>> ARRÊT : l'agent 7 n'est pas vérifié.", flush=True)
        return 7

    # ---------------- ÉTAPE 8 : Agent Diagnostic méthodologique ----------------
    if START <= 8:
        banner("[8/8] Agent Diagnostic méthodologique — modèle réel")
        from methodology_diagnostic_agent.core.config import get_settings as settings8
        from methodology_diagnostic_agent.llm.client import LLMClient as Client8
        from methodology_diagnostic_agent.pipeline import campaign as campaign8
        from methodology_diagnostic_agent.schemas.input import MethodologyRequest

        s = settings8()
        llm = Client8(s.llm_credentials(), s.limits)
        body = MethodologyRequest(
            student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
            main_research_question=results[5]["output"].get("main_research_question"),
            secondary_research_questions=results[5]["output"].get(
                "secondary_research_questions") or [],
            general_objective=results[6]["output"].get("general_objective"),
            specific_objectives=results[6]["output"].get("specific_objectives") or [],
            hypotheses=results[7]["output"].get("research_hypotheses") or [],
            literature_review=results[3]["output"].get("synthesis"),
            discipline="Sciences de gestion", academic_level="Master 2",
            country="Côte d'Ivoire", geographical_area="Abidjan", study_period="2020-2024",
            target_population="développeurs",
            student_constraints=DEPENDANCES_ETUDIANT,
            field_access="Enquête de terrain possible auprès des entreprises de services numériques.",
            available_data="Questionnaires, entretiens, données de suivi de projets.",
            upstream_subject=results[1]["output"], upstream_problem=results[2]["output"],
            upstream_problematic=results[4]["output"], upstream_question=results[5]["output"],
            upstream_objectives=results[6]["output"], upstream_hypotheses=results[7]["output"])
        res = campaign8.run(body, s, llm, allow_network=True)
        results[8] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                      "verifier": res.verifier.model_dump(mode="json") if res.verifier else None}
        save(8, results[8])
        print("statut           :", res.output.status.value)
        print("vérificateur     :", res.verifier_status)
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[8] = load(8)
        print("[8/9] reprise : sortie de l'agent 8 relue depuis le disque", flush=True)
    if results[8].get("verifier_status") != "verified":
        print(">>> ARRÊT : l'agent 8 n'est pas vérifié.", flush=True)
        return 8

    # ---------------- ÉTAPE 9 : Agent Méthodologie ----------------
    if START <= 9:
        banner("[9/9] Agent Méthodologie — modèle réel")
        from methodology_agent.core.config import get_settings as settings9
        from methodology_agent.llm.client import LLMClient as Client9
        from methodology_agent.pipeline import campaign as campaign9
        from methodology_agent.schemas.input import MethodologyRequest

        s = settings9()
        llm = Client9(s.llm_credentials(), s.limits)
        # Le diagnostic de l'étape 8 est le SOCLE : on le passe tel quel, avec sa décision étudiante.
        diagnostic = dict(results[8]["output"])
        diagnostic.setdefault("student_validation", {"decision": "accepted", "comment": ""})
        body = MethodologyRequest(
            student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
            discipline="Sciences de gestion", academic_level="Master 2",
            country="Côte d'Ivoire", geographical_area="Abidjan", study_period="2020-2024",
            target_population="développeurs",
            research_context="Entreprises de services numériques d'Abidjan.",
            field_access="Enquête de terrain possible auprès des entreprises de services numériques.",
            available_data="Questionnaires et entretiens à réaliser auprès des développeurs.",
            available_resources="Six mois de terrain, budget limité.",
            available_tools="Tableur et outil d'analyse de données.",
            upstream_subject=results[1]["output"], upstream_problem=results[2]["output"],
            upstream_literature=results[3]["output"], upstream_problematic=results[4]["output"],
            upstream_question=results[5]["output"], upstream_objectives=results[6]["output"],
            upstream_hypotheses=results[7]["output"],
            upstream_methodology_diagnostic=diagnostic)
        res = campaign9.run(body, s, llm, allow_network=False)
        results[9] = {"output": res.output.model_dump(mode="json"),
                      "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                      "verifier": res.verifier.model_dump(mode="json") if res.verifier else None}
        save(9, results[9])
        print("statut           :", res.output.status.value)
        print("document         :", res.output.document_status.value)
        print("vérificateur     :", res.verifier_status)
        covered = sum(1 for row in res.output.matrice.lignes if row.statut.value == "couverte")
        print("matrice          :", f"{covered}/{len(res.output.matrice.lignes)} objectifs couverts")
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[9] = load(9)
        print("[9/10] reprise : sortie de l'agent 9 relue depuis le disque", flush=True)
    if results[9].get("verifier_status") != "verified":
        print(">>> ARRÊT : l'agent 9 n'est pas vérifié.", flush=True)
        return 9

    # ---------------- ÉTAPE 10 : Agent Résultats et analyse ----------------
    if START <= 10:
        banner("[10/10] Agent Résultats et analyse — modèle réel")
        from research_results_analysis_agent.core.config import get_settings as settings10
        from research_results_analysis_agent.llm.client import LLMClient as Client10
        from research_results_analysis_agent.pipeline import campaign as campaign10
        from research_results_analysis_agent.schemas.input import Dataset, ResultsAnalysisRequest

        s = settings10()
        llm = Client10(s.llm_credentials(), s.limits)
        methodology = dict(results[9]["output"])
        methodology.setdefault("student_validation", {"decision": "accepted", "comment": ""})
        # Jeu de données FOURNI par l'« étudiant » du test : c'est une ENTRÉE, jamais une sortie
        # d'agent. L'agent 10 n'en invente aucune valeur — il la calcule.
        body = ResultsAnalysisRequest(
            student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
            discipline="Sciences de gestion", academic_level="Master 2",
            data_origin="Questionnaire administré auprès de développeurs en télétravail.",
            data_period="2024",
            collection_notes="Questionnaires administrés en ligne et en présentiel ; "
                             "une réponse incomplète conservée telle quelle.",
            datasets=[Dataset(nom="enquete-developpeurs", format="csv", contenu=DATASET_ETUDIANT,
                              source="Questionnaire administré par l'étudiant", periode="2024",
                              description="Réponses brutes, sans nettoyage préalable.")],
            upstream_subject=results[1]["output"], upstream_problem=results[2]["output"],
            upstream_literature=results[3]["output"], upstream_problematic=results[4]["output"],
            upstream_question=results[5]["output"], upstream_objectives=results[6]["output"],
            upstream_hypotheses=results[7]["output"],
            upstream_methodology_diagnostic=results[8]["output"],
            upstream_methodology=methodology)
        res = campaign10.run(body, s, llm, allow_network=False)
        results[10] = {"output": res.output.model_dump(mode="json"),
                       "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                       "verifier": res.verifier.model_dump(mode="json") if res.verifier else None}
        save(10, results[10])
        print("statut           :", res.output.status.value)
        print("document         :", res.output.document_status.value)
        print("vérificateur     :", res.verifier_status)
        print("calculs          :", len(res.output.computed_results.resultats), "résultats calculés")
        print("synthèse         :", len(res.output.synthese_pour_conclusion), "point(s) pour l'étape 11")
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[10] = load(10)
        print("[10/11] reprise : sortie de l'agent 10 relue depuis le disque", flush=True)
    if results[10].get("verifier_status") != "verified":
        print(">>> ARRÊT : l'agent 10 n'est pas vérifié.", flush=True)
        return 10

    # ---------------- ÉTAPE 11 : Agent Conclusion ----------------
    if START <= 11:
        banner("[11/11] Agent Conclusion — modèle réel")
        from research_conclusion_agent.core.config import get_settings as settings11
        from research_conclusion_agent.llm.client import LLMClient as Client11
        from research_conclusion_agent.pipeline import campaign as campaign11
        from research_conclusion_agent.schemas.input import ConclusionRequest

        s = settings11()
        llm = Client11(s.llm_credentials(), s.limits)
        results_up = dict(results[10]["output"])
        results_up.setdefault("student_validation", {"decision": "accepted", "comment": ""})
        methodology = dict(results[9]["output"])
        methodology.setdefault("student_validation", {"decision": "accepted", "comment": ""})
        body = ConclusionRequest(
            student_id=STUDENT, session_id=SESSION, subject_text=SUJET,
            discipline="Sciences de gestion", academic_level="Master 2",
            upstream_subject=results[1]["output"], upstream_problem=results[2]["output"],
            upstream_literature=results[3]["output"], upstream_problematic=results[4]["output"],
            upstream_question=results[5]["output"], upstream_objectives=results[6]["output"],
            upstream_hypotheses=results[7]["output"],
            upstream_methodology_diagnostic=results[8]["output"],
            upstream_methodology=methodology, upstream_results=results_up)
        res = campaign11.run(body, s, llm, allow_network=False)
        results[11] = {"output": res.output.model_dump(mode="json"),
                       "verifier_status": res.verifier_status, "llm_calls": res.llm_calls,
                       "verifier": res.verifier.model_dump(mode="json") if res.verifier else None}
        save(11, results[11])
        print("statut           :", res.output.status.value)
        print("document         :", res.output.document_status.value)
        print("vérificateur     :", res.verifier_status)
        print("résultats cités  :", len(res.output.references_resultats))
        print("sections         :", len(res.output.draft.sections))
        print("appels LLM       :", res.llm_calls, flush=True)
    else:
        results[11] = load(11)
        print("[11/11] reprise : sortie de l'agent 11 relue depuis le disque", flush=True)

    # ---------------- BILAN ----------------
    banner("BILAN DE LA CHAÎNE (sorties réelles)")
    ok = True
    for stage in range(1, 12):
        status = results[stage].get("verifier_status")
        flag = "OK " if status == "verified" else "!! "
        if status != "verified":
            ok = False
        print(f"  {flag}Agent {stage} : {status}")
    print("\nBILAN :", "CHAÎNE COMPLÈTE VÉRIFIÉE (1 → 11)" if ok else
          "CHAÎNE INCOMPLÈTE (voir ci-dessus)")
    print("sorties :", OUT)
    return 0 if ok else 9


if __name__ == "__main__":
    sys.exit(main())
