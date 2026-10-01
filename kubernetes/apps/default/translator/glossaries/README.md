# UK–France shared terminology

Six explicit directional glossaries for Translator v0.5.0, researched on
2026-10-02. The user requested shared access for all translator users.
These are curated translation aids, not certified legal equivalents or a
complete dictionary. Targets are editorial choices informed by official
sources; they must not be presented as translations endorsed by those bodies.

| Name prefix (each begins `UK–France`) | Direction | Authored rows | App rules |
| --- | --- | ---: | ---: |
| Family law | EN → FR | 46 | 179 |
| Family law | FR → EN | 44 | 143 |
| Personal taxes | EN → FR | 43 | 147 |
| Personal taxes | FR → EN | 44 | 152 |
| Household invoices, payslips & utilities | EN → FR | 66 | 248 |
| Household invoices, payslips & utilities | FR → EN | 74 | 239 |

317 authored rows expand to 1,108 rules, including case and apostrophe variants.
Select the appropriate direction in **Upload → Global settings → Glossaries**.
All three topics may be selected together for the same language pair. They
are optional: publication does not select them for users or alter existing jobs.

## Content decision

Keep operator-maintained public terminology here, outside the app Kustomization.
This folder is not mounted into the application or reconciled into database
records by Flux. JSON files are the public seed content; the app encrypts its
saved copies and owns revisions, permissions and job snapshots. No application
code, image, schema, credential, provider or secret-template change is needed.
This applies the app's
[Decision 0033](https://git.christfriedbalizou.app/christfried.balizou/translator/src/tag/v0.5.0/docs/decisions/0033-translation-controls.md)
without changing its behavior or triggering an unrelated application release.

Each TSV is an independently authored direction, with a source-reference key
and scope note for every row. Do not invert mappings automatically. `sources.json`
resolves those keys to official publications. Their dates describe the research
snapshot, not a guarantee that terminology or law will never change. No source
definitions or articles have been copied into the app.

`build.py` generates the six `GlossaryWrite` JSON payloads. It adds initial-capital
and uppercase forms, English heading capitalization, and straight/curly
apostrophe source variants. It does not invent plurals, remove accents, stem
words or perform fuzzy matching. Targets follow initial/uppercase source case;
preserve rules retain the exact matched spelling. Redundant identical rules
coalesce. Regenerate JSON after editing TSV content; never edit generated JSON
independently. Source notes stay in this folder because the app has no per-term
note field.

## Jurisdiction and matching boundaries

- France and the UK are not treated as one legal system. England/Wales order
  names, Scottish courts/procedures and Northern Irish divorce terminology
  have specific scope notes. Coverage of Scotland and NI is introductory,
  not exhaustive. Ofgem refers to Great Britain; Ofwat to England and Wales.
- `prestation compensatoire` is not silently converted to spousal maintenance.
  `autorité parentale` remains distinct from the broader treaty expression
  `responsabilité parentale`. PACS is not a UK civil partnership.
- Council Tax, NI domestic rates, French taxe d'habitation and taxe foncière
  remain distinct. National Insurance is not CSG/CRDS. French net social,
  taxable income and net pay are separate measures. No tax rates, liabilities,
  deadlines, eligibility rules or currency conversions are encoded.
- Distinct order/institution names are preserved or described with their
  original name. Generic ambiguous words such as `charge`, `order`, `garde`,
  `pension`, `maintenance`, `part` and `taux` are intentionally absent.
- P45/P60 and numbered legal references cannot be authored as rules because
  the app prohibits numbers in glossary terms. Their values remain protected
  by the existing translation pipeline. Standalone HT/TTC/NI are omitted to
  avoid ambiguous abbreviation substitutions; prefer full contextual phrases.
- Literal matching cannot match phrases split across PDF fragments or styling,
  and does not adjust grammar around fixed replacements. Review the output,
  particularly legal documents and long descriptive targets in narrow columns.
  No professional legal-linguist review or real-document PDF layout approval
  is claimed for this first edition.

## Sources

Primary references include [HCCH's bilingual child-protection convention](https://www.hcch.net/en/instruments/conventions/full-text/?cid=70),
[GOV.UK family guidance](https://www.gov.uk/looking-after-children-divorce/apply-for-court-order),
[Service Public family guidance](https://www.service-public.gouv.fr/particuliers/vosdroits/F38331),
[HMRC's UK–France tax convention](https://www.gov.uk/government/publications/france-tax-treaties/2008-uk-and-france-double-taxation-convention-in-force),
[DGFiP's international guidance](https://www.impots.gouv.fr/internationalenindividual/taxation-foreign-source-income),
[French payslip guidance](https://www.service-public.gouv.fr/particuliers/vosdroits/F559),
[Ofgem](https://www.ofgem.gov.uk/your-energy-supply/your-energy-bill/energy-price-cap-and-standing-charges-explained)
and [the French energy mediator's glossary](https://www.energie-info.fr/glossaire).
See [sources.json](sources.json) for the complete reference index. The Ofwat
metering page was available through indexed official excerpts; direct retrieval
returned 403. Its entries concern generic water-bill terminology only.

## Validation and import

From this directory, `python3 build.py --check` checks reproducibility. Run
`verify.py` with the matching Translator Python environment (not homelab's):

```sh
env -u PYTHONPATH -u VIRTUAL_ENV uv run --group dev python /absolute/path/to/glossaries/verify.py
```

The verifier checks the real app schema, all generated rule matches, byte
budgets, direction conflicts and the 14 synthetic cases in `checks.json`.
These are deterministic terminology checks, not an LLM quality benchmark.

`import_shared.py` is a privileged operator procedure, not a browser login or
a new app API. It uses the app's existing permission-checked, audited,
encrypted glossary service under the unique active administrator. It refuses
ambiguous administrator selection and conflicting existing records. A single
transaction creates all missing records, validates combined snapshots and
rolls back on failure. Re-running with identical content creates no duplicates
or new revisions. It never modifies an existing record, user, session or role.
Keys/settings are read inside the app runtime and are never copied out.

For an explicitly authorized import, run the following from this directory
after replacing the pod name with the current ready API pod. The example is
read-only; adding `--apply` to the command arguments performs the import.

```python
import json
import subprocess
from pathlib import Path

payloads = [json.loads(path.read_text()) for path in sorted(Path('.').glob('*-??-??.json'))]
command = ['kubectl', 'exec', '-i', 'CURRENT_TRANSLATOR_POD', '-c', 'app',
           '-n', 'default', '--', 'python', '-c', Path('import_shared.py').read_text()]
subprocess.run(command, input=json.dumps(payloads).encode(), check=True)
```

Run read-only mode again after apply to verify committed encrypted content
and both selections. Receipts contain counts and sizes only. Do not save
identities, credentials or private app exports here. Future terminology edits
require review and an explicit revision update through the normal app API/UI;
this create-only importer deliberately fails if an existing definition differs.
To stop using a glossary, deselect it. This does not alter saved job snapshots.

## Verification receipt

Local checks passed for all 1,108 rules and 14 representative cases. Combined
snapshots contain 556 EN→FR rules / 48,478 bytes and 520 FR→EN rules / 44,813
bytes, including revision references. Each glossary is below both deployed
authoring limits. Case/apostrophe variants account for the larger rule counts.

A disposable network-isolated container, using the current app backend and
synthetic SQLite data, verified read-only checking, full rollback after an
injected fourth-write failure, encrypted read-back, idempotence, refusal to
overwrite, six audit events, and visibility without edit/delete permission for
a regular user. The container and its temporary key/database were removed.

Live import on 2026-10-02 created all six shared records at revision 1 under
the existing sole active administrator. A separate read-only invocation found
all six exactly matching the payload fields, with no missing
records, and selected all three topics in each direction using the deployed
service. No existing glossary was present or replaced. The runtime kept keys
and account identifiers private. The API and worker image remained v0.5.0.
The deployed matcher passed the same 14 synthetic cases against the decrypted
saved records. All six `glossary.saved` audit events were present; both
containers remained Ready with zero restarts. No authenticated browser session
or real-document PDF translation was exercised in this content-only task.

Helper checks passed Black at 79 columns, isort's Black profile at 79 columns
with explicit four-space indentation (the homelab EditorConfig otherwise
defaults to two), flake8, and strict mypy against the Translator backend.
No Kubernetes manifests changed, so no render, reconcile or redeployment was
required. These glossaries are available immediately to signed-in users.
