# Olist Data Platform — Runbook (Windows PowerShell)

Every command here is PowerShell-native and assumes Windows. Run them in **Windows PowerShell 5.1** (the blue icon, built into Windows) or **PowerShell 7** (the black icon, if you have installed it) — the project works with either.

Replace `<your-username>` with your GitHub username throughout.

A note on how PowerShell differs from the bash instructions you may have seen elsewhere, because these three differences cause most of the confusion:

- Environment variables are set with `$env:NAME = "value"`, not `export NAME=value`, and they only last for the lifetime of that terminal window. Close the window and they are gone.
- Paths use backslashes: `data\raw`, not `data/raw`. PowerShell tolerates forward slashes in most places, but the commands below use backslashes consistently.
- `make` does not exist on Windows. The project ships `run_all.ps1` as the direct equivalent.

---

# STEP 1 — Run the pipeline locally

The point of this step is to prove the project works on your machine before it goes near GitHub. Roughly a minute of compute once the packages are installed.

## 1.1 Check your prerequisites

Open PowerShell (press `Win`, type `powershell`, press Enter) and run:

```powershell
python --version
git --version
```

You need Python 3.10 or newer. If `python` opens the Microsoft Store instead of printing a version, Python is not properly installed — get it from <https://www.python.org/downloads/> and **tick "Add python.exe to PATH"** on the first installer screen. If you have the Python launcher, `py --version` and `py -3.12 --version` also work; substitute `py` for `python` throughout if that is your setup.

If git is missing, install it from <https://git-scm.com/download/win> and accept the defaults.

Close and reopen PowerShell after installing either, so the new PATH is picked up.

## 1.2 Unzip the project and change into it

Unzip `olist-data-platform.zip` somewhere with a short path and no spaces — `C:\projects\` is ideal. Avoid OneDrive-synced folders: OneDrive locks files mid-write and can corrupt the DuckDB file while the pipeline runs.

```powershell
cd C:\projects\olist-data-platform
Get-ChildItem
```

You should see `README.md`, `Makefile`, `run_all.ps1`, `requirements.txt` and the folders `analysis`, `dbt`, `data`, `docs`, `ingestion`, `orchestration`, `quality`. If you instead see a single `olist-data-platform` folder, you are one level too high — `cd olist-data-platform`.

## 1.3 Put the raw CSVs in place

The CSVs are excluded from the zip and from git deliberately: they total about 120 MB, and GitHub rejects any single file over 100 MB. Copy the nine files you originally uploaded into `data\raw\`. If they are sitting in your Downloads folder:

```powershell
Copy-Item "$env:USERPROFILE\Downloads\olist_*.csv" -Destination .\data\raw\
Copy-Item "$env:USERPROFILE\Downloads\product_category_name_translation.csv" -Destination .\data\raw\
```

Verify the count:

```powershell
(Get-ChildItem .\data\raw\*.csv).Count
```

This must print `9`. To see exactly which files are there:

```powershell
Get-ChildItem .\data\raw\*.csv | Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
```

The names must match exactly — the loader looks them up by name and raises `FileNotFoundError: Missing raw file: ...`, naming the offender, if one is wrong. The geolocation file is the big one at about 58 MB; the translation file is tiny at 3 KB.

## 1.4 Create and activate the virtual environment

A virtual environment keeps this project's packages isolated from anything else on your machine.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`. That prefix is how you know the environment is active. It is per-terminal: every new PowerShell window needs `.\.venv\Scripts\Activate.ps1` again before you run project commands.

**If you get "running scripts is disabled on this system"** — this is the single most common Windows stumbling block. Windows blocks local scripts by default. Fix it once for your own user account:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Answer `Y`. This affects only your user, not the machine, and `RemoteSigned` still blocks unsigned scripts downloaded from the internet — it permits local ones like the activation script and `run_all.ps1`. Then run the activate command again.

## 1.5 Install the dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs duckdb, dbt-core, dbt-duckdb, sqlalchemy, pandas, matplotlib, great_expectations, dagster and Jupyter. Expect two to five minutes and a great deal of output; the final line should be `Successfully installed ...`.

Confirm the key tools resolve **to the virtual environment**, not to some other Python on your system:

```powershell
Get-Command python, dbt | Select-Object Name, Source
python -c "import duckdb, great_expectations, dagster; print('ok')"
dbt --version
```

The `Source` column should point inside `...\olist-data-platform\.venv\Scripts\`. If it points elsewhere, the environment is not active — go back to 1.4.

## 1.6 Run the whole pipeline

```powershell
.\run_all.ps1
```

That one command does everything: ingests the CSVs into DuckDB, runs the 20 dbt models, runs the 96 dbt tests, runs the Great Expectations gate, and generates the charts and KPIs. It prints a cyan `=== step name ===` banner before each stage, stops immediately if any stage fails, and reports the exit code of whatever broke.

Two switches are available:

```powershell
.\run_all.ps1 -Clean          # delete the warehouse and rebuild from scratch
.\run_all.ps1 -SkipAnalysis   # stop after the quality gate
```

Use `-Clean` whenever you want to prove reproducibility from nothing, which is worth doing once before you push.

### Running the stages by hand instead

If you would rather see each command — for a screenshot, or because a stage failed and you want to isolate it — this is exactly what the script runs. Note the two environment variables: they pin the warehouse file and the dbt profile to absolute paths so every tool agrees on one location regardless of which folder you are standing in.

```powershell
$env:DUCKDB_PATH      = "$PWD\data\warehouse\olist.duckdb"
$env:DBT_PROFILES_DIR = "$PWD\dbt\olist_dbt"

python .\ingestion\load_raw_duckdb.py --db $env:DUCKDB_PATH --raw .\data\raw

dbt run  --project-dir .\dbt\olist_dbt --profiles-dir $env:DBT_PROFILES_DIR --target duckdb
dbt test --project-dir .\dbt\olist_dbt --profiles-dir $env:DBT_PROFILES_DIR --target duckdb

python .\quality\run_great_expectations.py

Push-Location .\analysis
python .\run_analysis.py
Pop-Location
```

Run these from the repository root with the virtual environment active. `Push-Location`/`Pop-Location` are PowerShell's `pushd`/`popd` — they take you into `analysis\` and bring you back afterwards.

## 1.7 Check the output against what it should be

Four checkpoints, in order.

**Ingestion** — nine lines, ending:

```
INFO loaded orders                              99441 rows
INFO loaded products                            32951 rows
INFO loaded sellers                              3095 rows
INFO loaded product_category_translation           71 rows
```

**dbt run** — `Completed successfully` followed by `Done. PASS=20 WARN=0 ERROR=0 SKIP=0 TOTAL=20`. That is 8 staging views plus 12 analytics tables.

**dbt test** — `Done. PASS=74 WARN=2 ERROR=0 SKIP=0 TOTAL=76`.

Those two warnings are expected, and understanding them is worth a mark or two. They are the two singular tests deliberately configured with `severity='warn'`: 8 orders marked `delivered` that carry no delivery timestamp, and 246 orders whose payment differs from items plus freight by more than R$1 (vouchers and partial refunds). Both are genuine defects in the public Olist dataset. If an assessor asks why they are not errors: failing the build over documented upstream defects you cannot fix would block every future run, so the pipeline surfaces them as warnings and writes them up in `docs\report.md` §4 instead of hiding them.

**Great Expectations** — six `PASS` lines then `Overall: PASS`.

**Analysis** — a block of KPI JSON in the terminal, and new files on disk:

```powershell
Get-ChildItem .\analysis\outputs | Select-Object Name, Length
```

Seven PNGs (`01_monthly_revenue.png` through `07_volume_vs_late_rate.png`), seven CSVs and `kpis.json`. Open one to confirm it rendered:

```powershell
Invoke-Item .\analysis\outputs\05_delivery_days_by_state.png
```

You should see stacked bars with a thin blue band (seller handling, flat across every state) under a tall orange band (carrier transit, rising steeply for the northern states). That single picture is the backbone of your delivery argument.

### When something fails

| Symptom | Cause and fix |
|---|---|
| `running scripts is disabled on this system` | See 1.4 — set the execution policy for CurrentUser. |
| `Found 8 CSV files in data\raw - expected 9` | The script's preflight check. A CSV is missing or misnamed; list them with the command in 1.3. |
| `FileNotFoundError: Missing raw file` | Same cause, caught by the loader; the message names the file. |
| `dbt : The term 'dbt' is not recognized` | The virtual environment is not active. Re-run `.\.venv\Scripts\Activate.ps1`. |
| `Could not find profile named 'olist_dbt'` | `$env:DBT_PROFILES_DIR` is unset in this terminal, or you passed a relative path from the wrong folder. Re-set it as in 1.6. |
| `IO Error: database is locked` | A Jupyter kernel or `dagster dev` still holds the DuckDB file. Close them, or `Get-Process python \| Stop-Process`, then retry. |
| `Access to the path ... is denied` on the `.duckdb` file | OneDrive or an antivirus scanner has the file open. Move the project outside OneDrive. |
| GE fails on row counts | A partial or different copy of the dataset. Re-download from Kaggle. |

## 1.8 Two optional extras worth doing

**The Dagster lineage graph** — the single most useful screenshot for your slides, because it shows all 31 assets and their dependencies in one picture.

```powershell
$env:DAGSTER_HOME = "$PWD\.dagster_home"
New-Item -ItemType Directory -Force -Path $env:DAGSTER_HOME | Out-Null
Push-Location .\orchestration
dagster dev -f .\olist_dagster\definitions.py
```

Open <http://localhost:3000>, go to the **Assets** tab, click **View lineage**, then **Materialize all**. Watch the graph turn green left to right: nine `olist_raw/*` assets, then eight `staging/*`, then twelve `analytics/*`, then `quality_gate`, then `analysis_outputs`. Screenshot it and save as `docs\images\dagster_lineage.png`. Stop the server with `Ctrl+C`, then `Pop-Location`.

Setting `DAGSTER_HOME` is optional — without it Dagster warns and uses a temporary folder — but it keeps your run history between sessions. The folder is git-ignored.

**The notebooks** already contain their executed outputs, so they display correctly on GitHub without you running anything. To step through them yourself:

```powershell
jupyter lab .\analysis\notebooks\01_sales_readiness.ipynb
```

Run cells with `Shift+Enter`. Before running the pipeline again, shut the kernel down (**Kernel → Shut Down All Kernels**), or the DuckDB file stays locked.

---

# STEP 2 — Push to GitHub on a single `main` branch

The brief asks for "a GitHub repository in a single main branch with all code and documentation", so do not create feature branches.

## 2.1 Create the empty repository on GitHub

1. Sign in at <https://github.com>, click the **+** at top right → **New repository**.
2. **Repository name:** `olist-data-platform`
3. **Description:** `End-to-end data pipeline on the Olist Brazilian e-commerce dataset: Meltano/Python ingestion, BigQuery + DuckDB warehouse, dbt star schema, Great Expectations quality gates, Dagster orchestration.`
4. **Visibility:** Public, unless your cohort requires private — if private, add your assessor under **Settings → Collaborators** afterwards.
5. **Do not tick** "Add a README file", "Add .gitignore" or "Choose a license". The project already has a README and a `.gitignore`; pre-creating them on GitHub gives you a merge conflict on the first push.
6. **Create repository**. Leave the resulting page open — you need the URL from it.

## 2.2 Set your git identity (first time on this machine only)

```powershell
git config --global user.name "Grace Chung"
git config --global user.email "you@example.com"
```

Use the address attached to your GitHub account, or your commits will not be linked to your profile.

## 2.3 Initialise and inspect before committing

From the repository root:

```powershell
git init -b main
git add .
git status
```

**Read that output before you commit.** This is the one place where a mistake is tedious to undo. You should see roughly 60 files staged, and you must **not** see:

- anything ending `.csv` under `data\raw\` (120 MB; GitHub rejects files over 100 MB)
- `data\warehouse\olist.duckdb` (about 150 MB, and regenerable in a minute)
- `.venv\` (thousands of library files)
- `dbt\olist_dbt\target\` or `logs\`
- `quality\gx_results.json`

All are covered by `.gitignore`, so they should be absent. Confirm explicitly:

```powershell
git status --short | Select-String -Pattern '\.csv|\.duckdb|\.venv|target/'
```

That should return nothing at all. If it returns lines, check `.gitignore` is present in the root (`Get-ChildItem -Force | Where-Object Name -eq '.gitignore'`), then re-stage cleanly:

```powershell
git rm -r --cached . | Out-Null
git add .
git status --short | Select-String -Pattern '\.csv|\.duckdb'
```

A useful sanity check on total size before pushing — anything over ~10 MB deserves a second look:

```powershell
git count-objects -vH | Select-String 'size-pack'
```

## 2.4 Commit

```powershell
git commit -m "Olist data platform: ingestion, dbt star schema, quality gates, analysis, Dagster orchestration"
```

You will get a summary such as `60 files changed, 3400 insertions(+)`.

## 2.5 Connect to GitHub and push

Take the HTTPS URL from the page you left open, then:

```powershell
git remote add origin https://github.com/<your-username>/olist-data-platform.git
git push -u origin main
```

**On authentication** — GitHub stopped accepting account passwords over HTTPS in 2021, and this is where most people get stuck. When prompted, you need a **personal access token**, not your login password. On Windows you will usually get a browser popup from Git Credential Manager instead, which handles it for you: sign in there and you are done.

If you get a text prompt rather than a popup, create a token: GitHub → your avatar → **Settings** → **Developer settings** (bottom of the left sidebar) → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**. Give it a note, a 30-day expiry, tick the **repo** scope, generate, and copy it immediately — it is shown once. Paste it at the password prompt. Note that PowerShell shows nothing while you paste a password; that is normal, just press Enter.

A successful push ends with `branch 'main' set up to track 'origin/main'`.

## 2.6 Verify the repository renders

Refresh the GitHub page and check four things:

1. The README displays with the architecture diagram visible.
2. `docs/schema_design.md` renders the entity-relationship diagram as an actual diagram — GitHub draws Mermaid natively.
3. `analysis/notebooks/01_sales_readiness.ipynb` shows its tables and charts, because the notebooks were executed before packaging.
4. The branch selector says **main**, and there is only one branch.

## 2.7 Committing again later

Whenever you add something — the Dagster screenshot, the slide deck, a fix to the report:

```powershell
git add .
git commit -m "Add Dagster lineage screenshot"
git push
```

---

# STEP 3 — Enable continuous integration

Optional for the brief, but it directly evidences section 6 (orchestration via CI/CD) and section 4 (automated quality checks), and a green run is easy to show. The workflow at `.github\workflows\ci.yml` rebuilds the entire pipeline on DuckDB on every push, every pull request, and nightly at 06:00 UTC. Because the CSVs are not in the repository, it downloads them from Kaggle, which needs your API credentials stored as encrypted repository secrets.

## 3.1 Get your Kaggle API token

1. Sign in at <https://www.kaggle.com>, click your avatar → **Settings**.
2. Scroll to **API** → **Create New Token**. A `kaggle.json` file downloads.
3. Read the two values out of it without leaving the terminal:

```powershell
Get-Content "$env:USERPROFILE\Downloads\kaggle.json" | ConvertFrom-Json | Format-List
```

That prints `username` and `key`. Treat the key like a password, and never commit `kaggle.json` to the repository.

## 3.2 Add the two secrets to GitHub

In your repository (not your account) on GitHub:

1. **Settings** → left sidebar **Secrets and variables** → **Actions**.
2. **New repository secret**. Name `KAGGLE_USERNAME`, value the `username` from the JSON — no quotes, no braces, no trailing space. **Add secret**.
3. **New repository secret** again. Name `KAGGLE_KEY`, value the `key`. **Add secret**.

Both should now be listed. GitHub will never show their values again; that is expected.

## 3.3 Accept the dataset terms on Kaggle

The Kaggle API refuses to download a dataset whose terms you have not accepted, and the error is a bare `403` that explains nothing. Visit <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce> once while signed in and click the download button — you can cancel the actual download. This prevents the most common CI failure.

## 3.4 Trigger the workflow

It runs automatically on push, so it may already have run in step 2 — check the **Actions** tab. To run it deliberately:

1. **Actions** → left sidebar → **pipeline-ci**.
2. **Run workflow** dropdown on the right → **Run workflow**. (The `workflow_dispatch` trigger is already in the YAML for exactly this.)
3. Refresh; a run appears with a yellow dot. Click into it, then into the `pipeline` job, to watch the steps stream: install dependencies → download from Kaggle → ingest → `dbt build` → Great Expectations → analysis → upload artifact.

Three to six minutes end to end. A green tick means the whole pipeline reproduced from nothing on a clean Ubuntu machine, which is the strongest evidence of reproducibility you can put in front of an assessor.

## 3.5 Collect the evidence

Screenshot the green run for your slides. At the bottom of the completed run page there is an **Artifacts** section containing `analysis-outputs` — download it to confirm the charts were regenerated in CI, not just copied from your machine.

### If the run fails

| Failure point | Cause and fix |
|---|---|
| "Download raw data from Kaggle" → 401 | Secrets wrong or misnamed. Check for stray quotes, spaces or a trailing newline. |
| "Download raw data from Kaggle" → 403 | Dataset terms not accepted — see 3.3. |
| "Install dependencies" fails | A package version unavailable for the runner's Python; the workflow pins 3.12. Read the traceback for the offending package. |
| "dbt build" fails though it passed locally | Almost always a file that was never committed. Run `git status` locally and push what is missing. |

If CI proves troublesome and time is short, drop it — it is not a required deliverable, and the Dagster schedule already satisfies the orchestration section on its own. Do not let it block steps 1, 2 and 4.

---

# STEP 4 — Build the executive slide deck

The brief asks for 10 minutes plus 5 of Q&A to a mixed audience of business and technical executives. `docs\presentation_outline.md` gives 14 slides with per-slide timings summing to about 9 minutes 45, leaving a buffer.

## 4.1 Gather the assets

Everything you need already exists. Collect them into one folder so you are not hunting mid-build:

```powershell
New-Item -ItemType Directory -Force -Path .\docs\deck_assets | Out-Null
Copy-Item .\analysis\outputs\*.png .\docs\deck_assets\
Copy-Item .\docs\images\*.png       .\docs\deck_assets\
Invoke-Item .\docs\deck_assets
```

| Slide | Image |
|---|---|
| 3 — the business questions | `business_case.png` |
| 5 — when demand peaks | `01_monthly_revenue.png` |
| 6 — what sells | `03_categories_and_states.png` |
| 7 — who buys | `04_segment_revenue_share.png` |
| 8 — delivery, where | `05_delivery_days_by_state.png` |
| 9 — delivery, why | `07_volume_vs_late_rate.png` |
| 10 — technical overview | `architecture.png` |
| 10 or 11 — orchestration proof | `dagster_lineage.png` (from 1.8) |

The numbers for the KPI tiles on slides 4, 11 and 13 are in `analysis\outputs\kpis.json` and written up in `docs\report.md`. To read them in the terminal:

```powershell
Get-Content .\analysis\outputs\kpis.json | ConvertFrom-Json | ConvertTo-Json -Depth 5
```

## 4.2 Build the slides

Use PowerPoint, Google Slides or Keynote — whichever you present from most confidently. Work from `docs\presentation_outline.md`, which gives each slide a headline, its visual, and speaker notes. Three rules matter more than the template.

**One message per slide, stated as the headline.** "Seller handling is 2.7 days everywhere — the gap is the carrier" is a headline. "Delivery analysis" is not. Someone who reads only your headlines should still come away with the argument intact.

**Put the number in the headline and the evidence in the chart.** The charts are rendered at 130 dpi and project legibly, but nobody reads axis labels from the back of a room. They read the headline and trust the shape.

**Keep the technical slide credible but shallow.** Slide 10 is where you earn the CTO's confidence: one codebase targeting two warehouses, 124 automated checks, 31 orchestrated assets, full lineage. Do not walk the dbt DAG model by model — hold that for Q&A, where you can go as deep as the question warrants.

## 4.3 Rehearse against the clock

Presenters overrun on the architecture slide and the first findings slide. Time yourself once, end to end. If you are long, cut slides 2 and 4 rather than compressing the findings — the findings are what the audience came for.

Prepare the six questions at the foot of `docs\presentation_outline.md`. The likeliest, and the one with the best answer, is "how do we know the numbers are right?": 96 dbt tests and 28 expectations run on every build, the pipeline fails rather than publish bad data, and the two known source defects are documented rather than swept away.

## 4.4 Export and commit the deck

Export to PDF — it renders identically everywhere and displays inline on GitHub — then add it:

```powershell
Copy-Item "$env:USERPROFILE\Downloads\olist_executive_presentation.pdf" -Destination .\docs\
git add .\docs\olist_executive_presentation.pdf
git commit -m "Add executive presentation"
git push
```

Commit the editable `.pptx` too if it is under 100 MB; assessors sometimes want the speaker notes.

---

# Final check before you submit

Walk the deliverables against the live repository in your browser, not against your local folder:

- [ ] Single `main` branch, containing all code and documentation.
- [ ] README renders, architecture diagram visible.
- [ ] `analysis/notebooks/` holds two notebooks that display their outputs on GitHub.
- [ ] `docs/` holds the report, the schema-design justification and the presentation PDF.
- [ ] The Actions tab shows a green run (if you did step 3).
- [ ] You can answer in one sentence each: why a star schema, why dbt, why two warehouses, and what the two dbt warnings mean.

That last line is what tends to separate a good submission from a very good one. The code is demonstrably correct; the marks come from being able to justify it.
