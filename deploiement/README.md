# Déploiement — la plateforme tourne seule

Consigne du porteur : « ils seront en ligne, donc ils doivent être indépendants ». La plateforme ne
doit pas dépendre d'un démarrage manuel : elle se relève au démarrage du serveur et après un
plantage.

## Les deux services

| Service | Rôle | Type |
|---|---|---|
| `memo-agents` | les douze agents (un par étape) | `oneshot` + `RemainAfterExit` |
| `memo-orchestrateur` | l'orchestrateur, seul interlocuteur du site | `simple`, `Restart=on-failure` |

Les fichiers `.service` de ce dossier sont la copie versionnée de ceux installés dans
`/etc/systemd/system/`. En cas de modification, **modifier ici puis recopier** — sinon la copie
installée et la copie versionnée divergent en silence.

## Installation (à rejouer sur un nouveau serveur)

```bash
cp deploiement/systemd/memo-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now memo-agents memo-orchestrateur
```

## Vérification

```bash
systemctl is-active memo-agents memo-orchestrateur   # -> active, active
curl -s http://127.0.0.1:8000/agents | head -c 200   # -> "en_ligne": 12
```

## Pourquoi un script d'enrobage pour l'orchestrateur

`lancer-orchestrateur.sh` existe parce que `EnvironmentFile=` de systemd est fragile sur un fichier
d'environnement de 26 Ko : une ligne inattendue et le service ne démarre plus, sans message clair.
Le script charge l'environnement comme le ferait un démarrage manuel, puis remplace le shell par
uvicorn.

## Ce qui n'est PAS géré ici

- Le **site web** (l'interface étudiante) n'est pas dans ces services : c'est le site du porteur qui
  remplace celui construit ici.
- Les **sauvegardes** de `workspace/` (dossiers étudiants et base d'état) ne sont pas automatisées.
