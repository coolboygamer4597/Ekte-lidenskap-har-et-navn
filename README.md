# Versioned offsets

Offset packages for the goatgoatgoat test build. The client downloads only the package matching the running Roblox version.

The executable offers Automatic updates (recommended), Bundled offsets, and Local offsets file. Bundled offsets come from its own `offsets.h`. Local import accepts this dumper's header format or a package JSON file. Selected files are read as data; they are not executed.

## Publish an update

1. Install Python 3.9 or newer.
2. Open a terminal in this repository and run `python publish_offsets.py "C:\path\to\offsets.h"`.
3. Test the generated `versions/version-…/r….json` in the external using Local offsets file. Confirm the needed features work before publishing.
4. Publish the package and index together:

```powershell
git add index.json versions
git commit -m "Update offsets"
git push origin main
```

The script checks the required fields and version, creates a new revision, computes its SHA-256, and updates the index after the package exists. It never overwrites an existing revision or pushes automatically. Keep previous Roblox versions and revisions available. Do not publish personal paths, credentials, executables or game dumps.

## Correct or roll back an update

Stage a corrected header to create another revision for the same Roblox version. For rollback, point that version's index entry to an earlier revision and restore the SHA-256 for that exact file, then commit and push. The client checks the index on each launch in Automatic mode. It uses a verified cache when the network is unavailable; a missing published version or invalid package produces an error.

The initial package contains the offsets bundled in the local test source when this repository was prepared. No live game session was run by the setup tool. Numeric offsets do not replace program changes when Roblox changes feature behaviour or the required schema.

## Files

`schema.json` defines the fields required by schema 1. `index.json` selects one revision for each Roblox version. `versions/` holds the versioned packages. Header input uses namespace groups and literal decimal or hexadecimal values, with a `ClientVersion` string or unambiguous version annotation.
