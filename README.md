([Français](#fileshare-gui--application-locale-de-classification))

## FileShare-GUI

### What is this project?

FileShare-GUI is a local Windows application for records staff. It deduplicates files, extracts text, classifies documents against the FCP hierarchy in `fcp_CSV-UTF.csv`, lets a person correct the class, and writes metadata onto Office clones.

It runs on one workstation. After the Hugging Face models are saved on disk, the pipeline can run offline. It does not use Ollama or a cloud OCR service.

### How does it work?

The Gradio interface (`app.py`) runs these phases, in order:

1. **Deduplication** — exact and near-duplicate scan, Excel review, optional dry-run, then delete.
2. **Ingestion** — text from Office, PDF, images, and `.txt`. Vision images are saved under `extracted_texts/_images`.
3. **Classification** — one local embedder at a time (MiniLM, Qwen3-Embedding-0.6B, or Qwen3-Embedding-4B). Image captions use local Qwen2-VL when a file is vision-flagged.
4. **Review / override** — the reviewer picks Function, then Sub-Function, then Business Process from the FCP list. The same workbook is updated. Excerpt columns are cleared on override.
5. **Placeholders** — one JSON side-car per document, including Litigation_hold, Archival_value, and critical_business_content.
6. **Injector** — clones originals into a folder for that embedder. Word can receive built-in properties (Title, Subject, Tags) and custom properties (File → Info → Properties → Advanced Properties → Custom). The JSON side-car remains the full record.

Reports and clones stay separate per model (`classification_results_minilm.xlsx`, `classification_results_qwen3.xlsx`, `classification_results_qwen3_4b.xlsx`, and `Injected_Metadata\minilm`, `\qwen3`, `\qwen3_4b`).

**Setup (each machine)**

1. Download the ZIP from the repository, or `git clone` it, into a user-writable folder. Do not install under `Program Files`.
2. Create a virtual environment and install dependencies: `python -m venv .venv`, activate it, then `python -m pip install -r requirements.txt`. On a managed PC with no Conda, use the installed `py` and `py -m pip`.
3. Download the embedders and the vision model once (network required) into the folders named in `project_config.py`. Runtime is offline after that.
4. Edit absolute paths only in `project_config.py` (source documents, extracts, results, models, resources). Save and restart after any change.
5. From the project folder, run `py app.py` and open `http://127.0.0.1:7860`.

Stop cancels the current job. Files already written are kept. There is no undo.

Office injection needs a licensed Microsoft Office install and `pywin32` (Windows only). If COM injection fails, the JSON side-car is still written. PDF and plain-text files do not receive native Office properties.

### Who will use this project?

Records and information-management staff, and the analyst who configures paths on a managed Windows workstation. Reviewers correct classification in Excel or in the Review / override tab. It is not a public web service.

### What is the goal of this project?

Give staff a local, repeatable way to classify documents to the FCP hierarchy, keep a human in the loop, and carry the agreed metadata onto Office copies and JSON side-cars — without sending document text to an online model at runtime.

### How to Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md).

### License

Unless otherwise noted, the source code of this project is covered under Crown Copyright, Government of Canada, and is distributed under the [MIT License](LICENSE).

The Canada wordmark and related graphics associated with this distribution are protected under trademark law and copyright law. No permission is granted to use them outside the parameters of the Government of Canada's corporate identity program. For more information, see [Federal identity requirements](https://www.canada.ca/en/treasury-board-secretariat/topics/government-communications/federal-identity-requirements.html).

______________________

([English](#fileshare-gui))

## FileShare-GUI — application locale de classification

### Quel est ce projet?

FileShare-GUI est une application Windows locale destinée au personnel de gestion des documents. Elle repère les doublons, extrait le texte, classe les documents selon la hiérarchie du FCP dans `fcp_CSV-UTF.csv`, permet à une personne de corriger la classe, puis inscrit les métadonnées sur des copies Office.

Elle s’exécute sur un seul poste. Une fois les modèles Hugging Face enregistrés sur le disque, le pipeline peut fonctionner hors ligne. Elle n’utilise pas Ollama ni un service d’OCR infonuagique.

### Comment ça marche?

L’interface Gradio (`app.py`) enchaîne les phases suivantes :

1. **Déduplication** — repérage des doublons exacts et proches, examen dans Excel, essai à blanc facultatif, puis suppression.
2. **Ingestion** — texte tiré des fichiers Office, PDF, images et `.txt`. Les images pour la vision sont enregistrées sous `extracted_texts/_images`.
3. **Classification** — un seul modèle d’intégration à la fois (MiniLM, Qwen3-Embedding-0.6B ou Qwen3-Embedding-4B). Les légendes d’images utilisent Qwen2-VL en local lorsque le fichier est marqué pour la vision.
4. **Examen / remplacement** — la personne choisit la fonction, puis la sous-fonction, puis le processus opérationnel dans la liste du FCP. Le même classeur est mis à jour. Les colonnes d’extraits sont vidées en cas de remplacement.
5. **Espaces réservés** — un fichier JSON d’accompagnement par document, y compris Litigation_hold, Archival_value et critical_business_content.
6. **Injection** — copie des originaux dans un dossier propre au modèle. Word peut recevoir les propriétés intégrées (Titre, Sujet, Mots-clés) et les propriétés personnalisées (Fichier → Informations → Propriétés → Propriétés avancées → Personnalisation). Le JSON d’accompagnement demeure le dossier complet.

Les rapports et les copies restent séparés par modèle (`classification_results_minilm.xlsx`, `classification_results_qwen3.xlsx`, `classification_results_qwen3_4b.xlsx`, et `Injected_Metadata\minilm`, `\qwen3`, `\qwen3_4b`).

**Installation (chaque poste)**

1. Télécharger le ZIP du dépôt, ou faire un `git clone`, dans un dossier accessible en écriture. Ne pas installer sous `Program Files`.
2. Créer un environnement virtuel et installer les dépendances : `python -m venv .venv`, l’activer, puis `python -m pip install -r requirements.txt`. Sur un poste géré sans Conda, utiliser le `py` déjà installé et `py -m pip`.
3. Télécharger une fois les modèles d’intégration et le modèle de vision (réseau requis) dans les dossiers indiqués dans `project_config.py`. L’exécution est ensuite hors ligne.
4. Modifier les chemins absolus uniquement dans `project_config.py` (documents sources, extraits, résultats, modèles, ressources). Enregistrer et redémarrer après tout changement.
5. Depuis le dossier du projet, lancer `py app.py` et ouvrir `http://127.0.0.1:7860`.

Le bouton d’arrêt annule le travail en cours. Les fichiers déjà écrits sont conservés. Il n’y a pas d’annulation.

L’injection Office exige une installation sous licence de Microsoft Office et `pywin32` (Windows seulement). Si l’injection COM échoue, le JSON d’accompagnement est tout de même écrit. Les PDF et les fichiers texte ne reçoivent pas de propriétés Office natives.

### Qui utilisera ce projet?

Le personnel de gestion des documents et de l’information, et l’analyste qui configure les chemins sur un poste Windows géré. Les examinateurs corrigent la classification dans Excel ou dans l’onglet Examen / remplacement. Ce n’est pas un service Web public.

### Quel est le but de ce projet?

Offrir au personnel un moyen local et reproductible de classer les documents selon la hiérarchie du FCP, de garder une personne dans la boucle, et de reporter les métadonnées convenues sur des copies Office et des fichiers JSON d’accompagnement — sans envoyer le texte des documents à un modèle en ligne au moment de l’exécution.

### Comment contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md).

### Licence

Sauf indication contraire, le code source de ce projet est protégé par le droit d'auteur de la Couronne du gouvernement du Canada et distribué sous la [licence MIT](LICENSE).

Le mot-symbole « Canada » et les éléments graphiques connexes liés à cette distribution sont protégés en vertu des lois portant sur les marques de commerce et le droit d'auteur. Aucune autorisation n'est accordée pour leur utilisation à l'extérieur des paramètres du programme de coordination de l'image de marque du gouvernement du Canada. Pour obtenir davantage de renseignements à ce sujet, veuillez consulter les [Exigences pour l'image de marque](https://www.canada.ca/fr/secretariat-conseil-tresor/sujets/communications-gouvernementales/exigences-image-marque.html).
