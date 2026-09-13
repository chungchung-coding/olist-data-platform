# Olist Data Platform — Windows Runbook

Every command in this document is written for **PowerShell on Windows**, using the literal project path:

```
C:\Users\mbach\Documents\olist-data-platform
```

You can copy and paste each block as-is. If you ever move the project, replace that path everywhere and nothing else changes.

Three PowerShell habits to know before you start, because they cause most of the confusion when following instructions written for Mac or Linux:

- Environment variables are set with `$env:NAME = "value"`, never `export NAME=value`, and they last only for the life of that terminal window. Close the window and they are gone.
- Paths use backslashes: `data\raw`, not `data/raw`.
- `make` does not exist on Windows. This project ships `run_all.ps1` as the direct replacement.

---

# PART 0 — Set up the folder

## 0.1 Open PowerShell

Press `Win`, type `powershell`, and press Enter. You do **not** need "Run as administrator" for any step in this runbook.

You should get a window with a prompt like `PS C:\Users\mbach>`.

## 0.2 Check that Python and git are installed

```powershell
python --version
git --version
```

Expected: a Python version of 3.10 or higher, and any git version.

If `python` opens the Microsoft Store instead of printing a version, Python is not properly installed. Download it from <https://www.python.org/downloads/> and on the **first installer screen tick "Add python.exe to PATH"** before clicking Install — this is easy to miss and everything downstream depends on it.

If git is missing, install from <https://git-scm.com/download/win> and accept every default.

After installing either one, **close PowerShell and open a new window** so it picks up the updated PATH, then re-run the checks.

## 0.3 Check whether OneDrive is syncing your Documents folder

This matters. OneDrive holds files open while it uploads them, and the pipeline writes a large database file into the project. If OneDrive is syncing `Documents`, you can get `Access to the path is denied` errors part-way through a run.

```powershell
[Environment]::GetFolderPath('MyDocuments')
Test-Path C:\Users\mbach\Documents
```

Read the results together:

- If the first line prints `C:\Users\mbach\Documents` and the second prints `True`, your Documents folder is local. Nothing to do — carry on to 0.4.
- If the first line prints something containing `OneDrive`, such as `C:\Users\mbach\OneDrive\Documents`, then Windows has redirected your Documents folder into OneDrive. You have two options. Either pause syncing while you work (click the OneDrive cloud icon in the system tray → the gear icon → **Pause syncing** → 2 hours), or use a plain local folder instead by substituting `C:\projects\olist-data-platform` for the path everywhere in this runbook. Both work; pausing is less disruptive if you want to keep the exact path you asked for.
- If the second line prints `False`, the folder does not exist yet. Create it:

```powershell
New-Item -ItemType Directory -Force -Path C:\Users\mbach\Documents | Out-Null
```

## 0.4 Extract the project to the exact location

Find the downloaded zip first:

```powershell
Get-ChildItem C:\Users\mbach\Downloads\olist-data-platform*.zip
```

That should list one file. If the name differs slightly (browsers sometimes append `(1)`), use whatever name is shown in the next command.

Now extract it. The zip contains a single top-level folder called `olist-data-platform`, so extracting **to `Documents`** — not to `Documents\olist-data-platform` — produces exactly the path you want:

```powershell
Expand-Archive -Path C:\Users\mbach\Downloads\olist-data-platform.zip -DestinationPath C:\Users\mbach\Documents -Force
```

If Windows blocks it with a security warning about a file from the internet, unblock the zip first and repeat:

```powershell
Unblock-File -Path C:\Users\mbach\Downloads\olist-data-platform.zip
```

## 0.5 Verify what landed

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
Get-ChildItem
```

You should see the files `README.md`, `Makefile`, `run_all.ps1`, `requirements.txt`, `docker-compose.yml` and the folders `analysis`, `data`, `dbt`, `docs`, `ingestion`, `orchestration`, `quality`.

If instead you see a single folder named `olist-data-platform`, the archive nested itself one level deeper. Fix it by running:

```powershell
Move-Item C:\Users\mbach\Documents\olist-data-platform\olist-data-platform\* C:\Users\mbach\Documents\olist-data-platform\ -Force
Remove-Item C:\Users\mbach\Documents\olist-data-platform\olist-data-platform
```

Confirm the hidden files came across too, since `.gitignore` is essential later:

```powershell
Get-ChildItem -Force C:\Users\mbach\Documents\olist-data-platform | Where-Object Name -like ".*"
```

You should see `.github` and `.gitignore` listed.

---

# PART 1 — Run the pipeline on your machine

The point of this part is to prove everything works locally before it goes anywhere near GitHub. Allow about ten minutes, most of which is package installation.

## 1.1 Move into the project folder

Every command from here assumes you are in the project root. Start each new PowerShell session with:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
```

Confirm you are in the right place — this should print your project path:

```powershell
Get-Location
```

## 1.2 Put the nine raw CSVs into data\raw

The CSV files are deliberately not in the zip and not in git: they total about 120 MB, and GitHub rejects any single file over 100 MB. You need to supply them yourself.

If they are in your Downloads folder, copy them across:

```powershell
Copy-Item C:\Users\mbach\Downloads\olist_*.csv -Destination C:\Users\mbach\Documents\olist-data-platform\data\raw\
Copy-Item C:\Users\mbach\Downloads\product_category_name_translation.csv -Destination C:\Users\mbach\Documents\olist-data-platform\data\raw\
```

If they are somewhere else — say in a folder called `assignment data` on your Desktop — adjust the source path:

```powershell
Copy-Item "C:\Users\mbach\Desktop\assignment data\*.csv" -Destination C:\Users\mbach\Documents\olist-data-platform\data\raw\
```

Now verify. This must print exactly `9`:

```powershell
(Get-ChildItem C:\Users\mbach\Documents\olist-data-platform\data\raw\*.csv).Count
```

And check the names and sizes:

```powershell
Get-ChildItem C:\Users\mbach\Documents\olist-data-platform\data\raw\*.csv |
    Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}} |
    Format-Table -AutoSize
```

Expected, give or take rounding:

| File | Approx size |
|---|---|
| olist_customers_dataset.csv | 8.6 MB |
| olist_geolocation_dataset.csv | 58.4 MB |
| olist_order_items_dataset.csv | 14.7 MB |
| olist_order_payments_dataset.csv | 5.5 MB |
| olist_order_reviews_dataset.csv | 13.8 MB |
| olist_orders_dataset.csv | 16.8 MB |
| olist_products_dataset.csv | 2.3 MB |
| olist_sellers_dataset.csv | 0.2 MB |
| product_category_name_translation.csv | 0.0 MB |

The filenames must match exactly. The loader looks them up by name and will stop with `FileNotFoundError: Missing raw file: ...`, naming the one it could not find.

## 1.3 Allow local scripts to run, then create the virtual environment

Windows blocks local PowerShell scripts by default, which would stop both the environment activation script and `run_all.ps1`. Fix it once for your own user account:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Answer `Y` when prompted. This changes nothing for other users of the machine, and `RemoteSigned` still blocks unsigned scripts downloaded from the internet — it only permits local ones.

Now create the virtual environment, which keeps this project's packages isolated from anything else on your system:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Your prompt should change to something like:

```
(.venv) PS C:\Users\mbach\Documents\olist-data-platform>
```

That `(.venv)` prefix is how you know the environment is active. **It is per-window.** Every time you open a new PowerShell session to work on this project, run these two lines first:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\.venv\Scripts\Activate.ps1
```

## 1.4 Install the dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs duckdb, dbt-core, dbt-duckdb, sqlalchemy, pandas, matplotlib, great_expectations, dagster and Jupyter. Expect two to five minutes and a great deal of scrolling output. The last line should read `Successfully installed ...` followed by a long list.

Now confirm the tools resolve **to the virtual environment** and not to some other Python installation:

```powershell
Get-Command python, dbt | Select-Object Name, Source
```

Both `Source` values must start with `C:\Users\mbach\Documents\olist-data-platform\.venv\Scripts\`. If either points somewhere else, the environment is not active — go back to 1.3.

Two more quick checks:

```powershell
python -c "import duckdb, great_expectations, dagster, sqlalchemy; print('all imports ok')"
dbt --version
```

## 1.5 Run the entire pipeline with one command

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\run_all.ps1
```

This single script ingests the CSVs into DuckDB, runs the 20 dbt models, runs the 96 dbt tests, runs the Great Expectations quality gate, and generates the charts and KPI files. It prints a cyan `=== step name ===` banner before each stage, stops immediately if any stage fails, and reports the exit code of whatever broke rather than carrying on and producing half-built output.

The whole run takes roughly one minute.

Two switches are available:

```powershell
.\run_all.ps1 -Clean          # delete the warehouse first and rebuild from nothing
.\run_all.ps1 -SkipAnalysis   # stop after the quality gate, skip the charts
```

Run it once with `-Clean` before you push to GitHub. It proves the whole thing reproduces from scratch, which is exactly what an assessor wants to know.

### Running the stages individually

If you want to see each command separately — for a screenshot, or to isolate a failing stage — this is precisely what the script runs internally. Note the two environment variables at the top: they pin the warehouse file and the dbt profile to absolute paths, so every tool agrees on one location regardless of which folder you are standing in.

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\.venv\Scripts\Activate.ps1

$env:DUCKDB_PATH      = "C:\Users\mbach\Documents\olist-data-platform\data\warehouse\olist.duckdb"
$env:DBT_PROFILES_DIR = "C:\Users\mbach\Documents\olist-data-platform\dbt\olist_dbt"

python .\ingestion\load_raw_duckdb.py --db $env:DUCKDB_PATH --raw .\data\raw

dbt run  --project-dir .\dbt\olist_dbt --profiles-dir $env:DBT_PROFILES_DIR --target duckdb
dbt test --project-dir .\dbt\olist_dbt --profiles-dir $env:DBT_PROFILES_DIR --target duckdb

python .\quality\run_great_expectations.py

Push-Location .\analysis
python .\run_analysis.py
Pop-Location
```

`Push-Location` and `Pop-Location` are PowerShell's equivalents of `pushd` and `popd`: they take you into `analysis\` and bring you back afterwards.

## 1.6 Check the output against what it should be

Four checkpoints, in order.

**Ingestion** — nine lines, ending with:

```
INFO loaded orders                              99441 rows
INFO loaded products                            32951 rows
INFO loaded sellers                              3095 rows
INFO loaded product_category_translation           71 rows
```

**dbt run** — `Completed successfully`, then:

```
Done. PASS=20 WARN=0 ERROR=0 SKIP=0 TOTAL=20
```

That is 8 staging views plus 12 analytics tables.

**dbt test** — this one:

```
Done. PASS=74 WARN=2 ERROR=0 SKIP=0 TOTAL=76
```

The two warnings are expected, and understanding why is worth a mark or two in your viva. They are the two singular tests deliberately configured with `severity='warn'`: 8 orders marked `delivered` that carry no delivery timestamp, and 246 orders whose payment differs from items plus freight by more than R$1 (vouchers and partial refunds). Both are genuine defects in the public Olist dataset. If asked why they are not errors: failing the build over documented upstream defects that you cannot fix would block every future run, so the pipeline surfaces them as warnings and documents them in `docs\report.md` §4 rather than hiding them.

**Great Expectations** — six `PASS` lines, then:

```
Overall: PASS  (report: ...\quality\gx_results.json)
```

**Analysis** — a block of KPI JSON printed to the terminal, and new files on disk:

```powershell
Get-ChildItem C:\Users\mbach\Documents\olist-data-platform\analysis\outputs | Select-Object Name, Length
```

You should have seven PNGs (`01_monthly_revenue.png` through `07_volume_vs_late_rate.png`), seven CSVs and `kpis.json`.

Open the most important chart to confirm it rendered properly:

```powershell
Invoke-Item C:\Users\mbach\Documents\olist-data-platform\analysis\outputs\05_delivery_days_by_state.png
```

You should see stacked bars: a thin blue band (seller handling, flat at about 2.7 days in every state) beneath a tall orange band (carrier transit, rising steeply for the northern states). That one picture is the backbone of your delivery-readiness argument — the entire regional delivery gap is the carrier leg, not the sellers.

To confirm the warehouse itself was built:

```powershell
Get-ChildItem C:\Users\mbach\Documents\olist-data-platform\data\warehouse\olist.duckdb |
    Select-Object Name, @{n='MB';e={[math]::Round($_.Length/1MB,1)}}
```

Expect a file of roughly 80 MB.

## 1.7 When something goes wrong

| Symptom | Cause and fix |
|---|---|
| `run_all.ps1 cannot be loaded because running scripts is disabled` | Run the `Set-ExecutionPolicy` command in 1.3. |
| `Found 8 CSV files in data\raw - expected 9` | The script's own preflight check. Re-run the count command in 1.2 to see which is missing. |
| `FileNotFoundError: Missing raw file` | Same cause, caught by the loader; the message names the file. |
| `dbt : The term 'dbt' is not recognized` | The virtual environment is not active in this window. Run `.\.venv\Scripts\Activate.ps1`. |
| `Could not find profile named 'olist_dbt'` | `$env:DBT_PROFILES_DIR` is unset in this window. Use `.\run_all.ps1`, which sets it for you, or set it as in 1.5. |
| `IO Error: database is locked` | A Jupyter kernel or a `dagster dev` process still holds the DuckDB file. Close them, or run `Get-Process python \| Stop-Process -Force`, then try again. |
| `Access to the path ... olist.duckdb is denied` | OneDrive or antivirus has the file open. See 0.3 — pause OneDrive sync, or move the project to `C:\projects\`. |
| `ModuleNotFoundError: No module named 'duckdb'` | Dependencies installed into the wrong Python. Check `Get-Command python` points into `.venv`, then re-run `pip install -r requirements.txt`. |
| Great Expectations fails on row counts | A partial or different copy of the dataset. Compare your file sizes with the table in 1.2. |

If you need to start completely fresh at any point:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\run_all.ps1 -Clean
```

## 1.8 Two optional extras worth the time

### The Dagster lineage graph

This produces the single most impressive screenshot for your presentation: all 31 assets and their dependencies in one picture, proving the orchestration is real rather than theoretical.

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\.venv\Scripts\Activate.ps1

$env:DAGSTER_HOME = "C:\Users\mbach\Documents\olist-data-platform\.dagster_home"
New-Item -ItemType Directory -Force -Path $env:DAGSTER_HOME | Out-Null

Push-Location C:\Users\mbach\Documents\olist-data-platform\orchestration
dagster dev -f .\olist_dagster\definitions.py
```

Leave that running, then open <http://localhost:3000> in your browser. Go to the **Assets** tab, click **View lineage**, then **Materialize all**. Watch the graph turn green from left to right: nine `olist_raw/*` assets, then eight `staging/*`, then twelve `analytics/*`, then `quality_gate`, then `analysis_outputs`.

Screenshot the lineage view (`Win`+`Shift`+`S` opens the Windows snipping tool) and save it as:

```
C:\Users\mbach\Documents\olist-data-platform\docs\images\dagster_lineage.png
```

Then stop the server with `Ctrl+C` in the PowerShell window, and run `Pop-Location`.

Setting `DAGSTER_HOME` is optional — without it Dagster warns and uses a temporary folder — but it preserves your run history between sessions. That folder is already git-ignored.

### The notebooks

Both notebooks already contain their executed outputs, so they display correctly on GitHub without you running anything at all. If you want to step through them yourself:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\.venv\Scripts\Activate.ps1
jupyter lab .\analysis\notebooks\01_sales_readiness.ipynb
```

Run cells with `Shift`+`Enter`. When you are finished, shut the kernel down through **Kernel → Shut Down All Kernels** before running the pipeline again, otherwise the DuckDB file stays locked.

---

# PART 2 — Push to GitHub on a single `main` branch

The brief asks for "a GitHub repository in a single main branch with all code and documentation", so do not create feature branches.

## 2.1 Create the empty repository on GitHub

1. Sign in at <https://github.com>, click the **+** at the top right, then **New repository**.
2. **Repository name:** `olist-data-platform`
3. **Description:** `End-to-end data pipeline on the Olist Brazilian e-commerce dataset: Meltano/Python ingestion, BigQuery + DuckDB warehouse, dbt star schema, Great Expectations quality gates, Dagster orchestration.`
4. **Visibility:** Public, unless your cohort requires private — if private, add your assessor afterwards under **Settings → Collaborators**.
5. **Do not tick** "Add a README file", "Add .gitignore" or "Choose a license". The project already contains both a README and a `.gitignore`, and pre-creating them on GitHub produces a merge conflict on your very first push.
6. Click **Create repository** and leave the resulting page open — you need the URL from it in 2.5.

## 2.2 Set your git identity (first time on this machine only)

```powershell
git config --global user.name "Grace Chung"
git config --global user.email "you@example.com"
```

Use the email address attached to your GitHub account, otherwise your commits will not be linked to your profile.

## 2.3 Initialise the repository and inspect before committing

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
git init -b main
git add .
git status
```

**Read that `git status` output before you commit.** This is the one place in the whole process where a mistake is genuinely tedious to undo. You should see roughly 60 files staged, and you must **not** see:

- anything ending `.csv` under `data\raw\` — 120 MB, and GitHub hard-rejects files over 100 MB
- `data\warehouse\olist.duckdb` — about 80 MB, and rebuildable in a minute
- `.venv\` — thousands of library files
- `dbt\olist_dbt\target\` or `logs\`
- `quality\gx_results.json`
- `.dagster_home\`

All of these are covered by `.gitignore`, so they should already be absent. Confirm it explicitly — **this command should return nothing at all**:

```powershell
git status --short | Select-String -Pattern '\.csv|\.duckdb|\.venv|target/|dagster_home'
```

If it does return lines, check that `.gitignore` survived the extraction:

```powershell
Get-ChildItem -Force C:\Users\mbach\Documents\olist-data-platform\.gitignore
```

If it is missing, the extraction dropped hidden files; re-extract with `Expand-Archive` as in 0.4. If it is present, re-stage cleanly:

```powershell
git rm -r --cached . | Out-Null
git add .
git status --short | Select-String -Pattern '\.csv|\.duckdb'
```

A final sanity check on total size — anything above about 10 MB deserves a second look before you push:

```powershell
git count-objects -vH | Select-String 'size-pack'
```

## 2.4 Commit

```powershell
git commit -m "Olist data platform: ingestion, dbt star schema, quality gates, analysis, Dagster orchestration"
```

You will get a summary along the lines of `60 files changed, 3400 insertions(+)`.

## 2.5 Connect to GitHub and push

Take the HTTPS URL from the GitHub page you left open in 2.1 — it looks like `https://github.com/<your-username>/olist-data-platform.git` — then:

```powershell
git remote add origin https://github.com/<your-username>/olist-data-platform.git
git push -u origin main
```

**On authentication.** GitHub stopped accepting account passwords over HTTPS in 2021, and this is where most people get stuck. On Windows you will usually get a browser popup from Git Credential Manager: sign in there and it handles everything for you.

If you instead get a plain text prompt asking for a username and password, you need a **personal access token** rather than your password. Create one at GitHub → your avatar → **Settings** → **Developer settings** (at the very bottom of the left sidebar) → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**. Give it a note, a 30-day expiry, tick the **repo** scope, generate it, and copy it immediately — it is displayed only once. Paste that token at the password prompt. PowerShell shows nothing on screen while you paste a password; that is normal, just press Enter.

A successful push ends with `branch 'main' set up to track 'origin/main'`.

## 2.6 Verify the repository renders correctly

Refresh the GitHub page in your browser and check four things:

1. The README displays, with the architecture diagram visible.
2. `docs/schema_design.md` shows the entity-relationship diagram as an actual diagram — GitHub renders Mermaid natively.
3. `analysis/notebooks/01_sales_readiness.ipynb` displays its tables and charts, because the notebooks were executed before packaging.
4. The branch selector near the top left says **main**, and there is only one branch.

## 2.7 Committing again later

Every time you add something — the Dagster screenshot, the slide deck, a correction to the report:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
git add .
git commit -m "Add Dagster lineage screenshot"
git push
```

---

# PART 3 — Enable continuous integration

Optional for the brief, but it directly evidences section 6 (orchestration and CI/CD) and section 4 (automated quality checks), and a green run is easy evidence to show. The workflow at `.github\workflows\ci.yml` rebuilds the entire pipeline on DuckDB on every push, every pull request, and nightly at 06:00 UTC. Because the CSVs are not in the repository, it downloads them from Kaggle, which needs your API credentials stored as encrypted repository secrets.

## 3.1 Get your Kaggle API token

1. Sign in at <https://www.kaggle.com>, click your avatar, then **Settings**.
2. Scroll to the **API** section and click **Create New Token**. A file called `kaggle.json` downloads.
3. Read the two values out of it without leaving PowerShell:

```powershell
Get-Content C:\Users\mbach\Downloads\kaggle.json | ConvertFrom-Json | Format-List
```

That prints a `username` and a `key`. Treat the key like a password, and never copy `kaggle.json` into the project folder.

## 3.2 Add the two secrets to GitHub

In your repository on GitHub — the repository's own Settings, not your account settings:

1. **Settings** → left sidebar **Secrets and variables** → **Actions**.
2. **New repository secret**. Name it `KAGGLE_USERNAME`, paste the `username` value with no quotes, no braces and no trailing space. **Add secret**.
3. **New repository secret** again. Name it `KAGGLE_KEY`, paste the `key` value. **Add secret**.

Both should now appear in the list. GitHub will never display their values again, which is expected behaviour.

## 3.3 Accept the dataset terms on Kaggle

The Kaggle API refuses to download a dataset whose terms you have not accepted, and it fails with a bare `403` that explains nothing at all. Visit <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce> once while signed in and click the download button — you can cancel the actual download immediately. This prevents the most common CI failure.

## 3.4 Trigger the workflow

It runs automatically on push, so it may already have run when you pushed in Part 2 — check the **Actions** tab first. To run it deliberately:

1. **Actions** tab → in the left sidebar click **pipeline-ci**.
2. Click the **Run workflow** dropdown on the right, then the green **Run workflow** button. The `workflow_dispatch` trigger is already in the YAML for exactly this purpose.
3. Refresh after a few seconds. A run appears with a yellow dot; click into it, then into the `pipeline` job, to watch the steps stream past: install dependencies, download from Kaggle, ingest, `dbt build`, Great Expectations, analysis, upload artifact.

Three to six minutes end to end. A green tick means your entire pipeline reproduced from nothing on a clean Ubuntu machine — the strongest evidence of reproducibility you can put in front of an assessor.

## 3.5 Collect the evidence

Screenshot the green run for your slides. At the bottom of the completed run page there is an **Artifacts** section containing `analysis-outputs`; download it to confirm the charts were regenerated in CI rather than copied from your laptop.

### If the run fails

| Failure point | Cause and fix |
|---|---|
| "Download raw data from Kaggle" → 401 | Secrets wrong or misnamed. Check for stray quotes, spaces or a trailing newline in the values. |
| "Download raw data from Kaggle" → 403 | Dataset terms not accepted — see 3.3. |
| "Install dependencies" fails | A package version unavailable for the runner's Python; the workflow pins 3.12. Read the traceback for the offending package. |
| "dbt build" fails although it passed locally | Almost always a file that was never committed. Run `git status` locally and push whatever is missing. |

If CI proves troublesome and time is short, drop it. It is not a required deliverable, and the Dagster schedule in `orchestration\` already satisfies the orchestration section on its own. Do not let this block Parts 1, 2 and 4.

---

# PART 4 — Build the executive slide deck

The brief asks for 10 minutes plus 5 of Q&A, to a mixed audience of business and technical executives. `docs\presentation_outline.md` gives you 14 slides with per-slide timings summing to roughly 9 minutes 45, which leaves a small buffer.

## 4.1 Gather the assets into one folder

Everything you need already exists. Collect it so you are not hunting mid-build:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
New-Item -ItemType Directory -Force -Path .\docs\deck_assets | Out-Null
Copy-Item .\analysis\outputs\*.png .\docs\deck_assets\
Copy-Item .\docs\images\*.png .\docs\deck_assets\
Invoke-Item .\docs\deck_assets
```

That last line opens the folder in File Explorer so you can drag images straight into PowerPoint.

| Slide | Image |
|---|---|
| 3 — the business questions | `business_case.png` |
| 5 — when demand peaks | `01_monthly_revenue.png` |
| 6 — what sells | `03_categories_and_states.png` |
| 7 — who buys | `04_segment_revenue_share.png` |
| 8 — delivery, where | `05_delivery_days_by_state.png` |
| 9 — delivery, why | `07_volume_vs_late_rate.png` |
| 10 — technical overview | `architecture.png` |
| 10 or 11 — orchestration proof | `dagster_lineage.png`, from 1.8 |

The numbers for the KPI tiles on slides 4, 11 and 13 are all in `analysis\outputs\kpis.json` and written up in `docs\report.md`. To read them in the terminal:

```powershell
Get-Content C:\Users\mbach\Documents\olist-data-platform\analysis\outputs\kpis.json |
    ConvertFrom-Json | ConvertTo-Json -Depth 5
```

Open the outline itself alongside PowerPoint:

```powershell
Invoke-Item C:\Users\mbach\Documents\olist-data-platform\docs\presentation_outline.md
```

## 4.2 Build the slides

Use PowerPoint, Google Slides or Keynote — whichever you present from most confidently. Work slide by slide from `docs\presentation_outline.md`, which gives each one a headline, its visual, and speaker notes. Three rules matter more than the template you choose.

**One message per slide, stated as the headline.** "Seller handling is 2.7 days everywhere — the gap is the carrier" is a headline. "Delivery analysis" is not. Someone who reads only your headlines should still come away with your argument intact.

**Put the number in the headline and the evidence in the chart.** The charts render at 130 dpi and project legibly, but nobody reads axis labels from the back of a room. They read the headline and trust the shape of the picture.

**Keep the technical slide credible but shallow.** Slide 10 is where you earn the CTO's confidence: one codebase targeting two warehouses, 124 automated checks, 31 orchestrated assets, full lineage. Do not walk through the dbt DAG model by model — hold that for Q&A, where you can go as deep as the question deserves.

## 4.3 Rehearse against the clock

Presenters overrun on the architecture slide and on the first findings slide. Time yourself once, end to end. If you are long, cut slides 2 and 4 rather than compressing the findings — the findings are what the audience came for.

Prepare the six questions listed at the foot of `docs\presentation_outline.md`. The likeliest, and the one with the best answer, is "how do we know the numbers are right?" — 96 dbt tests and 28 expectations run on every build, the pipeline fails rather than publish bad data, and the two known source defects are documented rather than swept away.

## 4.4 Export and commit the deck

Export to PDF — it renders identically everywhere and displays inline on GitHub — then add it to the repository:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
Copy-Item C:\Users\mbach\Downloads\olist_executive_presentation.pdf -Destination .\docs\
git add .\docs\olist_executive_presentation.pdf
git commit -m "Add executive presentation"
git push
```

Commit the editable `.pptx` as well if it is under 100 MB; assessors sometimes want to read the speaker notes.

---

# Appendix A — The whole thing as one copy-paste block

For when you are starting from a fresh PowerShell window and everything is already installed:

```powershell
cd C:\Users\mbach\Documents\olist-data-platform
.\.venv\Scripts\Activate.ps1
.\run_all.ps1 -Clean
```

And the complete first-time setup, assuming Python and git are installed and the CSVs are in Downloads:

```powershell
Expand-Archive -Path C:\Users\mbach\Downloads\olist-data-platform.zip -DestinationPath C:\Users\mbach\Documents -Force
cd C:\Users\mbach\Documents\olist-data-platform
Copy-Item C:\Users\mbach\Downloads\olist_*.csv -Destination .\data\raw\
Copy-Item C:\Users\mbach\Downloads\product_category_name_translation.csv -Destination .\data\raw\
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
.\run_all.ps1
```

# Appendix B — Final check before you submit

Walk these against the live repository in your browser, not against your local folder:

- [ ] Single `main` branch, containing all code and documentation.
- [ ] README renders, with the architecture diagram visible.
- [ ] `analysis/notebooks/` holds two notebooks that display their outputs on GitHub.
- [ ] `docs/` holds the report, the schema-design justification and the presentation PDF.
- [ ] The Actions tab shows a green run, if you completed Part 3.
- [ ] You can answer, in one sentence each: why a star schema, why dbt, why two warehouses, and what the two dbt warnings mean.

That last line is what tends to separate a good submission from a very good one. The code is demonstrably correct; the marks come from being able to justify it.
