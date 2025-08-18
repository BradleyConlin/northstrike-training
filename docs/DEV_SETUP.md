Developer Setup
1) Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements-dev.txt
pre-commit install

2) Run local checks
pytest -q
pre-commit run --all-files

3) Standard PR flow

Create feature branch: git switch -c feat/<topic>

Commit & push: git add -A && git commit -m "feat: <desc>" && git push -u origin HEAD

Open PR: gh pr create --fill --base main
