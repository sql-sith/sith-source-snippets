# access_diff.py - readable before/after diff for access-review JSON

`access_diff.py` compares two JSON snapshots produced by the SQL Server access
collector and writes two files a person can read:

| Output | What it is |
|---|---|
| `<after>.access-diff.txt` | Narrative report: header with file hashes, summary table, warnings, then one plain-English line per change with the GUIDs to search for. |
| `<after>.access-diff.csv` | The same changes, one row each, with column titles. Opens directly in Excel. |

It is one file, standard library only, Python 3.9 or newer. Nothing to install
beyond Python itself.

## Where this fits in the review

1. Confirm which databases are in scope for SOX.
2. Run the collector. Keep that output as `before.json`.
3. Decide which permissions are privileged and which are over-allocated.
4. Remove the over-allocated permissions (and do the paperwork).
5. Run the **same version** of the collector again, as the same person. Keep that as `after.json`.
6. Run `access_diff.py before.json after.json`. Hand the auditors the two JSON files plus the `.txt` and `.csv` it produces.

The two JSON files remain the evidence. The diff is the index into them.

## Running it

Put `access_diff.py` and both JSON files somewhere you can find them, open a
terminal in that folder, and run one line. Output files land next to the AFTER
file.

### Windows

```
py -3 access_diff.py before.json after.json
```

If `py` is not recognized, try `python access_diff.py before.json after.json`.
If that opens the Microsoft Store or says "Python was not found", Python is not
installed: see Troubleshooting below.

### macOS

Open Terminal (Cmd+Space, type Terminal, Enter). Then:

```
cd ~/Downloads/wherever-you-put-the-files
python3 access_diff.py before.json after.json
```

Tip: you can type `python3 access_diff.py ` and then drag the two JSON files
from Finder into the Terminal window. Terminal fills in the full paths.

### Linux

```
python3 access_diff.py before.json after.json
```

### Options

```
python3 access_diff.py BEFORE.json AFTER.json [--csv FILE] [--report FILE] [--allow-mismatch]
```

- `--csv FILE`, `--report FILE`: write the outputs somewhere other than next to AFTER.
- `--allow-mismatch`: continue even if the two files disagree on instance, environment
  or collector schema version. Without it the script refuses (exit 1), because comparing
  two different servers produces nonsense that looks like thousands of removals.

## What the script prints

The console shows the report header, the summary table, every warning, and a
`RESULT:` line that states the exit code in words. When there are more than 40
detail lines they are left out of the console and you are pointed at the report
file.

```
RESULT: 7 access removal(s), 1 addition(s), 4 change(s) documented.
        NOTE: additions are out of scope for an access-removal review. Verify each one.
        1 integrity WARNING(s) need a human look - listed above and in the report. Returning exit code 2.
Report: C:\reviews\SQLPROD01\after.access-diff.txt
CSV:    C:\reviews\SQLPROD01\after.access-diff.csv
```

### Exit codes

| Code | Meaning | What to do |
|---|---|---|
| 0 | Ran fine. Changes may or may not exist; nothing suspicious about the files. | Attach the outputs. |
| 1 | Could not run: file missing, not JSON, or the two files are from different instances. | Fix the input. Nothing was written. |
| 2 | Ran, but found something a human should look at (see WARNINGS). Outputs were still written. | Read the warnings. Usually the data is still usable. |

Things that produce a warning (exit 2):

- Records found in the wrong array (a `Users` record inside `Principals`). The
  collector never does this; it means a file was edited by hand.
- A section missing from one file.
- A record that references a database / user / role / AD account that does not exist in the same file.
- Both files have the same `CollectedAtUtc` (AFTER is probably an edited copy of BEFORE).
- AFTER collected earlier than BEFORE (files given in the wrong order).
- The collector ran with different permissions in the two runs (missing data would look like removed access).
- Objects that match by name but carry a different GUID.

## Reading the report

Each change is one line, grouped by database (server-level items and AD group
expansion have their own groups):

```
Database: OrdersDb
  [Grants] Group CORP\DB-Reviewers: VIEW DATABASE STATE (database scope) was revoked in database OrdersDb
      GrantGuid: AED2B5DE-...   UserGuid: 34B48D6C-...   DatabaseGuid: B9DF7596-...
```

- `[Grants]` is the JSON array the object lives in.
- The sentence uses names. The line beneath lists GUIDs: first the object's own
  GUID, then the principal and database GUIDs. Search the JSON for any of them.
- Removed objects are in the BEFORE file. Added objects are in the AFTER file.
  Changed objects are in both.

Sections of the report, in order: `ACCESS REMOVED` (the point of the exercise),
`ACCESS CHANGED ON MATCHED OBJECTS` (same grant, fewer permissions; WITH GRANT
OPTION turned off; AD account disabled), `ACCESS ADDED` (should be empty in a
removal review - verify each one), `CONTEXT CHANGES` (databases, procedures,
listeners; not access), and `SECTIONS WITH NO CHANGES` so the auditor has the
negative confirmed.

### What counts as a change

| Reported | Not reported |
|---|---|
| Object present in BEFORE, absent in AFTER (Removed) | Timestamps (`CreateDate`) |
| Object present in AFTER, absent in BEFORE (Added) | Collector statistics (`ExecDetail`, `AdLoginCount`, `AdExpansionStatus`) |
| Grant permission list changed (`DELETE, INSERT` -> `INSERT`) | Field order, whitespace, array order |
| Grant `WithGrantOption` or `ObjCount` changed | Any field not listed on the left |
| User `LoginMapping` changed (for example MAPPED -> ORPHANED) | |
| AD account `Enabled` changed | |

Cascades are not rolled up. If a user is dropped from a database, you get one
row for the user, one for each role membership it had, and one for each grant.
That is the same grain as the JSON, which is the grain the review works at.

## CSV columns

| Column | Content |
|---|---|
| `Section` | JSON array the object came from (`Grants`, `RoleMemberships`, ...) |
| `Change` | `Removed`, `Added` or `Changed` |
| `Summary` | The same sentence as in the report |
| `Database` | Database name (blank for server-level and AD rows) |
| `Principal` | The user / login / group / AD account the row is about |
| `PrincipalType` | `SQL_USER`, `WINDOWS_GROUP`, `DATABASE_ROLE`, `AD_USER`, ... |
| `Role` | Role or AD group involved, if any |
| `Permission`, `Scope`, `GrantType` | Grant details (`SELECT`, `OBJECT`, `RO`, ...) |
| `Field`, `Before`, `After` | Filled only for `Changed` rows |
| `ObjectGuidField`, `ObjectGuid` | The object's own identity, e.g. `GrantGuid` and its value. Search the JSON for `ObjectGuid`. |
| `DatabaseGuid`, `PrincipalGuid`, `RoleGuid` | Related GUIDs for the same purpose |
| `FoundIn` | `before` for Removed, `after` for Added, `both` for Changed |

UTF-8 with BOM, CRLF line endings, so Excel opens it with the right characters
without an import wizard.

## Troubleshooting

### Windows: "python is not recognized" or the Microsoft Store opens

Python is not installed (the Store thing is a placeholder Windows ships). Any of:

- `winget install Python.Python.3.12` in a terminal, then open a new terminal.
- Download from <https://www.python.org/downloads/windows/>. On the first installer
  screen tick **Add python.exe to PATH**.
- If you already use `uv`: `uv run --python 3.12 --no-project python access_diff.py before.json after.json`
  (uv downloads Python itself the first time).

After installing, `py -3 --version` should print a version.

### macOS: a popup asks to install "command line developer tools"

That is normal on a Mac that has never run `python3`. Click **Install**, wait for it
to finish (a few minutes), then run the command again. If the popup does not appear
and you get `xcode-select: note: no developer tools were found`, run
`xcode-select --install` once.

If that route fails, install Python directly: <https://www.python.org/downloads/macos/>
(the "macOS 64-bit universal2 installer"), or `brew install python` if you have
Homebrew. Then use `python3` as shown above.

### macOS: "permission denied" or "command not found: access_diff.py"

Do not run the script as `./access_diff.py`. Always put `python3` in front:
`python3 access_diff.py before.json after.json`.

### Any OS: "No such file or directory"

The terminal is not in the folder with the files, or a path has a space in it.
Either `cd` into the folder first, or quote the paths:
`python3 access_diff.py "C:\My Reviews\before.json" "C:\My Reviews\after.json"`.
On macOS, dragging the file into the Terminal window pastes a correctly quoted path.

### "the two files do not describe the same instance"

You passed files from two different servers, or two different collector versions.
Check the paths. If it really is intentional, add `--allow-mismatch`.

### Garbled characters in the report on Windows

The report file itself is fine (UTF-8). It is the console font. Open the `.txt`
in Notepad or VS Code.

## Maintenance

Everything schema-specific is at the top of `access_diff.py`:

- `SECTION_ORDER`, `LABELS`, `ACCESS_SECTIONS`: which arrays exist and how they are labeled.
- `GUID_FIELD`: which field identifies an object in each array.
- `WATCHED_FIELDS`: which field changes on a matched object count as access changes.
- `SHAPES`: how to recognize a record type by its fields (used to detect misfiled records).
- `MUST_MATCH_*`: what must agree between the two files before a comparison is allowed.

Sentences live in `sentence()` and `change_sentence()`.

### Tests

```
python3 tests/run_tests.py path/to/a/real/collector-output.json
```

This builds a before/after fixture pair from one real file (a known set of
removals, partial revokes, a re-minted GUID, an added grant, noise that must stay
silent), runs the script through every exit path and checks counts and sentences.
`tests/fixtures/` is generated from real data: never share it.
