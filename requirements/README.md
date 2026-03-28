# Generated Requirements

This directory contains generated Python dependency views derived from skills/install-manifest.json.

Files:
- requirements.txt at the repo root: union of required Python packages for all registered skills
- requirements/skills/<skill>.txt: transitive Python packages required for one registered skill

Important:
- These files only describe Python packages.
- Use skills/install-manifest.json for binaries, node packages, post-install steps, and dependent skill folders.
