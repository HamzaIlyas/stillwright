# Windows

Stillwright's skills and `sw` work on Windows. The differences are small and listed here.

## Install `sw`

PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/HamzaIlyas/stillwright/releases/latest/download/stillwright-installer.ps1 | iex"
```

The installer places `sw.exe` under `CARGO_HOME\bin` (by default `%USERPROFILE%\.cargo\bin`)
and prints whether it updated your user PATH. Open a new terminal, then:

```sh
sw --version
```

`skills/stillwright/scripts/get-sw.sh` is a POSIX shell script and is not used on Windows;
agents on Windows should give you the PowerShell line above instead.

## Where state lives

`%USERPROFILE%\.stillwright\` (for example `C:\Users\you\.stillwright\`), or under `HOME` if
that variable is set. Set `STILLWRIGHT_HOME` to move it. All files are plain JSON and Markdown.

## Running on a schedule

Use Task Scheduler: a Basic Task, trigger "Daily, repeat every 1 hour", action
`cmd /c cd /d C:\work && claude -p "Use the stillwright skill: run one loop, then stop."`.
The same unattended rules apply: no pushes, deploys, publishing or new tools without a card.

## Known differences

- Symbolic links inside a pinned tool are hashed by their target path, not followed. Rust
  reports junctions as symlinks too, so they should get the same treatment; we have not
  tested this on Windows.
- The symlink test in the suite is skipped on Windows (creating symlinks needs privileges).
- Paths in run references: a bare word is a run name or slug; to pass a folder, include a
  separator (`.\runs\...` or a full path).
