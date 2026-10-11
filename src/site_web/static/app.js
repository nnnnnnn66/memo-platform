/* Accompagnement du mémoire — dynamisme du site.
 *
 * AUCUNE dépendance, aucun appel réseau, aucun code injecté : ce fichier est servi par la
 * plateforme elle-même (politique de sécurité : script-src 'self'). Tout ce qui suit est
 * progressif — si le JavaScript ne s'exécute pas, le site reste entièrement utilisable.
 */
(function () {
  'use strict';

  // Marquage immédiat : la classe « js » autorise les effets d'apparition. Posée par le script
  // lui-même, donc sans JavaScript le contenu RESTE VISIBLE (aucun risque de page vide).
  document.documentElement.classList.add('js');

  /* ---------------------------------------------------------------- barre latérale */
  function barreLaterale() {
    var bouton = document.querySelector('[data-bascule-laterale]');
    if (!bouton) return;
    bouton.addEventListener('click', function () {
      var ouvert = document.body.classList.toggle('laterale-ouverte');
      bouton.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
    });
    document.addEventListener('keydown', function (evenement) {
      if (evenement.key === 'Escape') document.body.classList.remove('laterale-ouverte');
    });
  }

  /* ------------------------------------------- apparition douce au défilement */
  function apparition() {
    var cibles = document.querySelectorAll('[data-apparait]');
    if (!cibles.length) return;
    if (!('IntersectionObserver' in window)) {
      cibles.forEach(function (cible) { cible.classList.add('visible'); });
      return;
    }
    var observateur = new IntersectionObserver(function (entrees) {
      entrees.forEach(function (entree) {
        if (!entree.isIntersecting) return;
        entree.target.classList.add('visible');
        observateur.unobserve(entree.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    cibles.forEach(function (cible) { observateur.observe(cible); });
  }

  /* ------------------------------------------------------- anneau de progression */
  function anneau() {
    var anneau = document.querySelector('[data-anneau]');
    if (!anneau) return;
    var part = parseFloat(anneau.getAttribute('data-anneau')) || 0;
    var cercle = anneau.querySelector('circle.jauge');
    if (!cercle) return;
    var perimetre = 2 * Math.PI * cercle.r.baseVal.value;
    cercle.style.strokeDasharray = perimetre;
    cercle.style.strokeDashoffset = perimetre;
    requestAnimationFrame(function () {
      cercle.style.transition = 'stroke-dashoffset 900ms cubic-bezier(.22,.61,.36,1)';
      cercle.style.strokeDashoffset = perimetre * (1 - part);
    });
  }

  /* ------------------------------------------------------------------- messages */
  function messages() {
    document.querySelectorAll('.message[data-efface]').forEach(function (message) {
      var fermer = document.createElement('button');
      fermer.type = 'button';
      fermer.className = 'message-fermer';
      fermer.setAttribute('aria-label', 'Masquer ce message');
      fermer.textContent = '×';
      fermer.addEventListener('click', function () { message.remove(); });
      message.appendChild(fermer);
      if (message.dataset.efface === 'auto') {
        setTimeout(function () {
          message.style.transition = 'opacity .5s, transform .5s';
          message.style.opacity = '0';
          message.style.transform = 'translateY(-6px)';
          setTimeout(function () { message.remove(); }, 520);
        }, 9000);
      }
    });
  }

  /* ----------------------------------------------- palette de commandes (Ctrl/Cmd+K) */
  function palette() {
    var racine = document.querySelector('[data-palette]');
    if (!racine) return;
    var champ = racine.querySelector('input');
    var liste = racine.querySelector('[data-resultats]');
    var entrees = Array.prototype.slice.call(racine.querySelectorAll('[data-entree]'));
    var selection = 0;

    function filtrer(texte) {
      var cherche = (texte || '').toLowerCase().trim();
      var vus = 0;
      entrees.forEach(function (entree) {
        var correspond = !cherche || entree.textContent.toLowerCase().indexOf(cherche) !== -1;
        entree.hidden = !correspond;
        if (correspond) vus += 1;
      });
      selection = 0;
      surligner();
      return vus;
    }
    function visibles() { return entrees.filter(function (e) { return !e.hidden; }); }
    function surligner() {
      entrees.forEach(function (e) { e.classList.remove('choisie'); });
      var listeVisible = visibles();
      if (listeVisible[selection]) {
        listeVisible[selection].classList.add('choisie');
        listeVisible[selection].scrollIntoView({ block: 'nearest' });
      }
    }
    function ouvrir() {
      racine.hidden = false;
      champ.value = '';
      filtrer('');
      champ.focus();
    }
    function fermer() { racine.hidden = true; }

    document.addEventListener('keydown', function (evenement) {
      if ((evenement.metaKey || evenement.ctrlKey) && evenement.key.toLowerCase() === 'k') {
        evenement.preventDefault();
        racine.hidden ? ouvrir() : fermer();
        return;
      }
      if (racine.hidden) return;
      if (evenement.key === 'Escape') { fermer(); }
      if (evenement.key === 'ArrowDown') {
        evenement.preventDefault(); selection = Math.min(selection + 1, visibles().length - 1);
        surligner();
      }
      if (evenement.key === 'ArrowUp') {
        evenement.preventDefault(); selection = Math.max(selection - 1, 0); surligner();
      }
      if (evenement.key === 'Enter') {
        var cible = visibles()[selection];
        if (cible) { window.location.href = cible.getAttribute('href'); }
      }
    });
    champ.addEventListener('input', function () { filtrer(champ.value); });
    racine.addEventListener('click', function (evenement) {
      if (evenement.target === racine) fermer();
    });
    var declencheur = document.querySelector('[data-ouvre-palette]');
    if (declencheur) {
      declencheur.addEventListener('click', function (evenement) {
        evenement.preventDefault(); ouvrir();
      });
    }
  }

  /* --------------------------------------- compteur de caractères des zones de texte */
  function compteurs() {
    document.querySelectorAll('textarea[data-compteur]').forEach(function (zone) {
      var afficheur = document.createElement('p');
      afficheur.className = 'aide-champ compteur';
      zone.parentNode.appendChild(afficheur);
      function maj() {
        afficheur.textContent = zone.value.trim().length + ' caractère' +
          (zone.value.trim().length > 1 ? 's' : '') + ' écrit' +
          (zone.value.trim().length > 1 ? 's' : '');
      }
      zone.addEventListener('input', maj);
      maj();
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    barreLaterale(); apparition(); anneau(); messages(); palette(); compteurs();
  });
})();
