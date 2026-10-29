//! sw: the state keeper for Stillwright. Plain files in $STILLWRIGHT_HOME (default ~/.stillwright):
//!
//!   profile.md       what the user told us (written during onboarding)
//!   notes.json       what we learned ourselves: dated, sourced, retired when contradicted
//!   goals.json       the work queue
//!   inbox.json       the only way we talk to the user: ask | review | notify | idea
//!   tools.lock.json  third-party tools we trust, pinned by content hash
//!   runs/<id>/       plan.md + log.jsonl per piece of work

use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::io::{Read as _, Write};

mod gate;
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode};
use std::time::Instant;

use clap::{Parser, Subcommand, ValueEnum};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

/// Left out of a tool's hash: VCS metadata and files the OS or Python regenerate by merely
/// running or browsing the tool (they would make every check cry wolf). Vendored
/// dependencies and build output stay in, because the tool runs that code.
const HASH_SKIP: &[&str] = &[".git", "__pycache__", ".DS_Store"];

type Result<T> = std::result::Result<T, String>;

// ---------------------------------------------------------------- data

#[derive(Serialize, Deserialize, Clone)]
struct Goal {
    id: u64,
    text: String,
    priority: u8,
    status: String,
    created: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    closed: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    note: Option<String>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Card {
    id: u64,
    kind: Kind,
    title: String,
    #[serde(default)]
    body: String,
    #[serde(default)]
    run: String,
    status: String,
    created: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    answer: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    answered: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    closed: Option<String>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Note {
    id: u64,
    text: String,
    kind: NoteKind,
    source: String,
    valid_from: String,
    valid_to: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    retired_reason: Option<String>,
}

#[derive(Serialize, Deserialize, Clone)]
struct Tool {
    name: String,
    path: String,
    #[serde(default)]
    source: String,
    sha256: String,
    pinned: String,
}

/// Inbox kinds, in the order the user should see them.
#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, ValueEnum, Debug)]
#[serde(rename_all = "lowercase")]
enum Kind {
    Ask,
    Review,
    Notify,
    Idea,
}

#[derive(Serialize, Deserialize, Clone, Copy, ValueEnum, Debug)]
#[serde(rename_all = "lowercase")]
enum NoteKind {
    Fact,
    Preference,
    Constraint,
}

impl Kind {
    fn name(self) -> &'static str {
        match self {
            Kind::Ask => "ask",
            Kind::Review => "review",
            Kind::Notify => "notify",
            Kind::Idea => "idea",
        }
    }
}

impl NoteKind {
    fn name(self) -> &'static str {
        match self {
            NoteKind::Fact => "fact",
            NoteKind::Preference => "preference",
            NoteKind::Constraint => "constraint",
        }
    }
}

// ---------------------------------------------------------------- cli

#[derive(Parser)]
#[command(
    name = "sw",
    version,
    about = "Stillwright state keeper",
    disable_help_subcommand = true
)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    /// One-screen summary: profile, goals, inbox, last run
    Status,
    /// Print the state folder
    Home,
    /// The work queue
    #[command(subcommand)]
    Goal(GoalCmd),
    /// Plans and logs for pieces of work
    #[command(subcommand)]
    Run(RunCmd),
    /// The only channel to the user: ask | review | notify | idea
    #[command(subcommand)]
    Inbox(InboxCmd),
    /// Things learned about the user, with source and validity
    #[command(subcommand)]
    Note(NoteCmd),
    /// Third-party tools pinned by content hash
    #[command(subcommand)]
    Tool(ToolCmd),
    /// Turn Stillwright on by default for everyone who opens a repository
    Init(InitArgs),
    /// Read a Claude Code session transcript and name the turns that broke the prompt cache
    Cache {
        /// Path to the session .jsonl (Claude Code keeps them under ~/.claude/projects/)
        file: PathBuf,
    },
    /// Judge a shell command before it runs: allow (exit 0), ask (3) or block (2), with the
    /// resolved paths and the blast radius. `--hook` speaks Claude Code's PreToolUse JSON.
    Gate(GateArgs),
    /// The cheapest model that passes for a route (`who:` in plans), from logged results
    Route { who: String },
    /// Lessons learned, with provenance, votes, scope and expiry
    #[command(subcommand)]
    Lesson(LessonCmd),
}

#[derive(clap::Args)]
struct GateArgs {
    /// Print the decision as JSON
    #[arg(long)]
    json: bool,
    /// Read a PreToolUse event on stdin and answer with a permission decision
    #[arg(long)]
    hook: bool,
    /// The folder the command may touch (default: the current directory)
    #[arg(long)]
    workspace: Option<PathBuf>,
    /// The command line to judge
    #[arg(trailing_var_arg = true)]
    command: Vec<String>,
}

#[derive(clap::Args)]
struct InitArgs {
    /// Repository folder (default: current directory)
    #[arg(long, default_value = ".")]
    dir: PathBuf,
    /// Only write .claude/settings.json (Claude Code)
    #[arg(long)]
    claude_only: bool,
    /// Only write .github/copilot/settings.json (GitHub Copilot)
    #[arg(long)]
    copilot_only: bool,
}

#[derive(Subcommand)]
enum GoalCmd {
    Add {
        text: String,
        #[arg(long, default_value_t = 3, value_parser = clap::value_parser!(u8).range(1..=5))]
        priority: u8,
    },
    List {
        #[arg(long)]
        all: bool,
    },
    Done {
        id: u64,
        #[arg(long)]
        note: Option<String>,
    },
}

#[derive(Subcommand)]
enum RunCmd {
    New {
        slug: String,
        #[arg(long)]
        goal: Option<u64>,
    },
    /// Append key=value pairs to a run's log (run: an id, a path, or "latest")
    Log {
        run: String,
        #[arg(required = true)]
        pairs: Vec<String>,
    },
    Status {
        #[arg(default_value = "latest")]
        run: String,
    },
    List,
    /// Money spent in a run: sums logged `model=`, `in=`, `out=` tokens at prices.json rates
    Cost {
        #[arg(default_value = "latest")]
        run: String,
    },
    /// Run a step's `$ <command>` check here and write a receipt (exit code, output hash,
    /// working-tree hash) to the run's log. A receipt is evidence; `sw run done` is the claim.
    Check {
        run: String,
        step: String,
    },
    /// Mark a step done. Needs a passing receipt taken on the working tree as it is now.
    Done {
        run: String,
        step: String,
    },
    /// Record the hashes of the files a step's checks depend on (tests, scripts). Any change
    /// afterwards fails the check as tampering until they are frozen again.
    Freeze {
        run: String,
        #[arg(required = true)]
        paths: Vec<String>,
    },
    /// Save the working tree (untracked files included) as a git snapshot for a step, before
    /// starting it. `sw run done` takes one on its own.
    Snapshot {
        run: String,
        step: String,
    },
    /// Put the working tree back as it was in a step's snapshot. The state being replaced is
    /// saved first, so a rewind can itself be undone.
    Rewind {
        run: String,
        step: String,
    },
    /// The goal, the must-nots and the next step of the open run, in a few lines: what must
    /// survive a context compaction. Prints nothing when no run is open.
    Brief,
    /// Steps that can start now: not passed yet, and every step in their `after:` passed.
    Next {
        #[arg(default_value = "latest")]
        run: String,
    },
    /// Across all runs: steps, pass rate and dollars per passed step for each (who, model)
    Stats,
    /// The review packet for a step: goal, constraints, the step and its check, the diff since
    /// the last snapshot and the latest check output. Nothing the worker said about the step;
    /// a fresh reviewer judges the work, then logs `result=pass|fail evidence=<verdict file>`.
    Review {
        run: String,
        step: String,
    },
}

#[derive(Subcommand)]
enum LessonCmd {
    /// Record a lesson with where it came from
    Add {
        text: String,
        /// `global`, or a word from the goals it applies to (a failure lesson stays scoped)
        #[arg(long, default_value = "global")]
        scope: String,
        /// self | reviewer | user | tool | web (tool and web are quarantined until trusted)
        #[arg(long, default_value = "self")]
        source: String,
        #[arg(long, default_value = "")]
        run: String,
        /// Days until it expires unless a vote renews it
        #[arg(long, default_value_t = 90)]
        days: i64,
    },
    /// Lessons in force (`--all`: expired and quarantined too)
    List {
        #[arg(long)]
        all: bool,
    },
    /// Mark a lesson helpful (`up`, also renews it) or harmful (`down`) after a step used it
    Vote { id: u64, direction: String },
    /// Take a tool- or web-sourced lesson out of quarantine
    Trust { id: u64 },
    /// The few lessons that apply to a goal, best first
    For {
        goal: String,
        #[arg(long)]
        all: bool,
        #[arg(long, default_value_t = 5)]
        limit: usize,
    },
}

#[derive(Serialize, Deserialize, Clone)]
struct Lesson {
    id: u64,
    text: String,
    scope: String,
    source: String,
    #[serde(default)]
    run: String,
    #[serde(default)]
    helpful: u32,
    #[serde(default)]
    harmful: u32,
    created: String,
    valid_until: String,
}

/// Open questions allowed per run.
const ASK_BUDGET: usize = 3;
/// Days a vote up adds to a lesson's life.
const LESSON_RENEWAL_DAYS: i64 = 90;

#[derive(Subcommand)]
enum InboxCmd {
    Add {
        kind: Kind,
        title: String,
        #[arg(long)]
        body: Option<String>,
        #[arg(long)]
        run: Option<String>,
    },
    List {
        #[arg(long)]
        all: bool,
    },
    Show {
        id: u64,
    },
    /// Record the user's reply; the card stays visible until it is applied and closed
    Answer {
        id: u64,
        answer: String,
    },
    Close {
        id: u64,
        #[arg(long)]
        answer: Option<String>,
    },
}

#[derive(Subcommand)]
enum NoteCmd {
    Add {
        text: String,
        #[arg(long)]
        source: String,
        #[arg(long, value_enum, default_value_t = NoteKind::Fact)]
        kind: NoteKind,
    },
    List {
        #[arg(long)]
        all: bool,
    },
    Retire {
        id: u64,
        #[arg(long)]
        reason: String,
    },
}

#[derive(Subcommand)]
enum ToolCmd {
    Pin {
        name: String,
        path: PathBuf,
        #[arg(long)]
        source: Option<String>,
        /// Re-pin a tool whose content changed (only after re-vetting it)
        #[arg(long)]
        force: bool,
    },
    Check,
    List,
}

// ---------------------------------------------------------------- storage

struct Store {
    root: PathBuf,
}

/// The state folder: `$STILLWRIGHT_HOME`, else `~/.stillwright`.
fn state_root() -> Result<PathBuf> {
    match std::env::var_os("STILLWRIGHT_HOME").filter(|v| !v.is_empty()) {
        Some(v) => {
            std::path::absolute(PathBuf::from(v)).map_err(|e| format!("STILLWRIGHT_HOME: {e}"))
        }
        None => Ok(home_dir()?.join(".stillwright")),
    }
}

impl Store {
    fn open() -> Result<Self> {
        let root = state_root()?;
        fs::create_dir_all(root.join("runs"))
            .map_err(|e| format!("cannot create {}: {e}", root.display()))?;
        Ok(Store { root })
    }

    /// Serialise read-modify-write so a scheduled run and a live session can't lose updates.
    fn lock(&self) -> Result<File> {
        // read+write, not append-only: Windows' LockFileEx denies locks on append-only handles.
        let file = OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .truncate(false)
            .open(self.root.join(".lock"))
            .map_err(|e| format!("cannot open lock file: {e}"))?;
        file.lock().map_err(|e| format!("cannot lock state: {e}"))?;
        Ok(file)
    }

    fn load<T: DeserializeOwned>(&self, name: &str) -> Result<Vec<T>> {
        let path = self.root.join(name);
        let text = match fs::read_to_string(&path) {
            Ok(t) => t,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
            Err(e) => return Err(format!("cannot read {}: {e}", path.display())),
        };
        if text.trim().is_empty() {
            return Ok(Vec::new());
        }
        serde_json::from_str(&text).map_err(|e| {
            format!(
                "{} is not valid JSON ({e}); fix or move it aside, then retry",
                path.display()
            )
        })
    }

    fn save<T: Serialize>(&self, name: &str, items: &[T]) -> Result<()> {
        let path = self.root.join(name);
        let tmp = self.root.join(format!(".tmp-{name}"));
        let json = serde_json::to_string_pretty(items).map_err(|e| e.to_string())?;
        fs::write(&tmp, json).map_err(|e| format!("cannot write {}: {e}", tmp.display()))?;
        fs::rename(&tmp, &path).map_err(|e| format!("cannot replace {}: {e}", path.display()))
    }

    fn runs(&self) -> Result<Vec<PathBuf>> {
        let mut runs: Vec<PathBuf> = fs::read_dir(self.root.join("runs"))
            .map_err(|e| e.to_string())?
            .filter_map(|e| e.ok().map(|e| e.path()))
            .filter(|p| p.is_dir())
            .collect();
        runs.sort();
        Ok(runs)
    }

    fn resolve_run(&self, reference: &str) -> Result<PathBuf> {
        let runs = self.runs()?;
        if reference.is_empty() || reference == "latest" {
            return runs
                .last()
                .cloned()
                .ok_or_else(|| "no runs yet".to_string());
        }
        // A reference is a path only when written as one; a bare word is a run name or slug,
        // so a same-named folder in the working directory cannot hijack it.
        let path = PathBuf::from(reference);
        if reference.contains(['/', '\\']) || reference.starts_with('.') {
            let runs_dir = fs::canonicalize(self.root.join("runs")).map_err(|e| e.to_string())?;
            let given = fs::canonicalize(&path).map_err(|e| e.to_string())?;
            if given.parent() == Some(runs_dir.as_path()) {
                return Ok(given);
            }
            return Err(format!(
                "{reference} is not a run folder under {}",
                runs_dir.display()
            ));
        }
        // Exact folder name, or the slug after the "YYYYMMDD-HHMMSS-" prefix; newest wins.
        runs.into_iter()
            .rfind(|p| {
                let name = file_name(p);
                name == reference || name.get(16..) == Some(reference)
            })
            .ok_or_else(|| format!("no run matching {reference}"))
    }
}

fn home_dir() -> Result<PathBuf> {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .ok_or_else(|| "cannot find home folder; set STILLWRIGHT_HOME".to_string())
}

fn now() -> String {
    chrono::Local::now().format("%Y-%m-%dT%H:%M:%S").to_string()
}

fn file_name(p: &Path) -> String {
    p.file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_default()
}

fn next_id(ids: impl Iterator<Item = u64>) -> u64 {
    ids.max().unwrap_or(0) + 1
}

fn find<T>(items: &mut [T], id: u64, get: fn(&T) -> u64) -> Result<&mut T> {
    items
        .iter_mut()
        .find(|i| get(i) == id)
        .ok_or_else(|| format!("no item with id {id}"))
}

// ---------------------------------------------------------------- runs

/// A plan step is a line like "3. do x | who: ... | check: ...". Only lines with a check count.
fn plan_steps(plan: &str) -> Vec<String> {
    plan.lines()
        .filter_map(|line| {
            let digits: String = line.chars().take_while(|c| c.is_ascii_digit()).collect();
            let rest = &line[digits.len()..];
            if digits.is_empty() || !rest.starts_with('.') {
                return None;
            }
            let has_check = rest
                .split('|')
                .skip(1)
                .any(|part| part.trim_start().starts_with("check:"));
            has_check.then_some(digits)
        })
        .collect()
}

/// Results per step. A pass logged by hand (not certified by `sw run done`) counts only while
/// the plan's check for that step is still the prose it was logged against: editing plan.md
/// around the log call, or back to a `$` command, does not turn it into a pass.
fn step_results(run: &Path, plan: &str) -> BTreeMap<String, String> {
    let mut results = BTreeMap::new();
    let text = fs::read_to_string(run.join("log.jsonl")).unwrap_or_default();
    for (n, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<serde_json::Map<String, serde_json::Value>>(line) {
            Ok(event) => {
                if let (Some(step), Some(result)) = (event.get("step"), event.get("result")) {
                    let step = value_str(step);
                    let mut result = value_str(result);
                    let certified = event.get("certified") == Some(&serde_json::Value::Bool(true));
                    if result == "pass" && !certified {
                        let current = plan_step_check(plan, &step);
                        let is_command = current.as_deref().and_then(command_check).is_some();
                        let recorded = event.get("check").map(value_str);
                        if is_command || (recorded.is_some() && recorded != current) {
                            result = "pass logged by hand, but the plan's check changed since (does not count)".into();
                        }
                    }
                    results.insert(step, result);
                }
            }
            Err(_) => eprintln!(
                "warning: {}/log.jsonl line {} is not JSON, skipped",
                file_name(run),
                n + 1
            ),
        }
    }
    results
}

fn value_str(v: &serde_json::Value) -> String {
    v.as_str()
        .map(str::to_string)
        .unwrap_or_else(|| v.to_string())
}

struct Progress {
    next: Option<String>,
    steps: Vec<String>,
    results: BTreeMap<String, String>,
}

impl Progress {
    fn of(run: &Path) -> Self {
        let plan = fs::read_to_string(run.join("plan.md")).unwrap_or_default();
        let steps = plan_steps(&plan);
        let results = step_results(run, &plan);
        let next = steps
            .iter()
            .find(|s| results.get(*s).map(String::as_str) != Some("pass"))
            .cloned();
        Progress {
            next,
            steps,
            results,
        }
    }

    fn total(&self) -> usize {
        self.steps.len()
    }

    fn passed(&self) -> usize {
        self.steps
            .iter()
            .filter(|s| self.results.get(*s).map(String::as_str) == Some("pass"))
            .count()
    }

    /// What to do next, worded the same everywhere it is shown.
    fn next_label(&self) -> String {
        match (&self.next, self.total()) {
            (Some(s), _) => format!("step {s}"),
            (None, 0) => "write plan.md".into(),
            (None, _) => "none, all passed".into(),
        }
    }
}

fn append_event(run: &Path, pairs: &[(String, String)]) -> Result<()> {
    let mut event = serde_json::Map::new();
    for (k, v) in pairs {
        event.insert(k.clone(), v.clone().into());
    }
    append_json(run, event)
}

fn append_json(run: &Path, mut event: serde_json::Map<String, serde_json::Value>) -> Result<()> {
    event.insert("ts".into(), now().into());
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(run.join("log.jsonl"))
        .map_err(|e| format!("cannot open run log: {e}"))?;
    writeln!(file, "{}", serde_json::Value::Object(event)).map_err(|e| e.to_string())
}

// ---------------------------------------------------------------- certificates
//
// A step whose check is written `check: $ <command>` is proven, not claimed: `sw run check`
// runs the command and writes a receipt (command, exit code, output hash, hash of the working
// tree, which frozen files were touched); `sw run done` accepts the step only if the latest
// receipt passed and the working tree is still the one it was taken on. A pass logged by
// hand for such a step is refused. Check files frozen with `sw run freeze` fail the check as
// tampered when they change, so weakening a test leaves a mark in the log.

/// The check text of one step in plan.md, if that step exists. A `$` command keeps its pipes:
/// it runs to the end of the line, minus a trailing `| after: …` field.
fn plan_step_check(plan: &str, step: &str) -> Option<String> {
    plan.lines().find_map(|line| {
        let digits: String = line.chars().take_while(|c| c.is_ascii_digit()).collect();
        let rest = &line[digits.len()..];
        if digits != step || !rest.starts_with('.') {
            return None;
        }
        let mut offset = 0;
        for part in rest.split('|') {
            if let Some(check) = part.trim_start().strip_prefix("check:") {
                let check = check.trim();
                if !check.starts_with('$') {
                    return Some(check.to_string());
                }
                let whole = rest[offset + (part.len() - part.trim_start().len())..].trim();
                let whole = whole.strip_prefix("check:").unwrap_or(whole).trim();
                // Trailing plan fields end the command; so a command cannot contain them.
                let end = ["| after:", "| who:"]
                    .iter()
                    .filter_map(|field| whole.find(field))
                    .min();
                let whole = match end {
                    Some(i) => whole[..i].trim(),
                    None => whole,
                };
                return Some(whole.to_string());
            }
            offset += part.len() + 1;
        }
        None
    })
}

/// A check sw can run itself: `$ <command>` (the space matters: `$5 refund shown` is prose).
fn command_check(check: &str) -> Option<&str> {
    check
        .strip_prefix("$ ")
        .map(str::trim)
        .filter(|c| !c.is_empty())
}

/// Top folder of the git repository the current directory is in.
fn git_top() -> Option<String> {
    git(None, &[], &["rev-parse", "--show-toplevel"])
}

/// Run git in `dir` with extra environment; stdout on success, None otherwise.
fn git(dir: Option<&str>, envs: &[(&str, &Path)], args: &[&str]) -> Option<String> {
    let mut cmd = Command::new("git");
    cmd.args(args);
    if let Some(dir) = dir {
        cmd.current_dir(dir);
    }
    for (key, value) in envs {
        cmd.env(key, value);
    }
    match cmd.output() {
        Ok(out) if out.status.success() => {
            Some(String::from_utf8_lossy(&out.stdout).trim().to_string())
        }
        _ => None,
    }
}

/// A fresh path under the temp folder for a throw-away index or object store.
fn temp_git_path(kind: &str) -> PathBuf {
    let path = std::env::temp_dir().join(format!(
        "sw-{kind}-{}-{}",
        std::process::id(),
        now().replace([':', 'T', '-'], "")
    ));
    let _ = fs::remove_file(&path);
    let _ = fs::remove_dir_all(&path);
    path
}

/// A throw-away index, and (unless objects are kept) a throw-away object store layered over
/// the repository's, so staging the working tree leaves nothing behind. Removed on drop.
struct TempStore {
    index: PathBuf,
    objects: Option<PathBuf>,
    alternate: Option<PathBuf>,
}

impl TempStore {
    fn new(top: &str, keep_objects: bool) -> Result<Self> {
        let index = temp_git_path("index");
        if keep_objects {
            return Ok(TempStore {
                index,
                objects: None,
                alternate: None,
            });
        }
        let git_dir = git(Some(top), &[], &["rev-parse", "--absolute-git-dir"])
            .ok_or_else(|| format!("git cannot read the repository at {top}"))?;
        let objects = temp_git_path("objects");
        fs::create_dir_all(&objects).map_err(|e| format!("cannot create a temp store: {e}"))?;
        Ok(TempStore {
            index,
            objects: Some(objects),
            alternate: Some(PathBuf::from(git_dir).join("objects")),
        })
    }

    fn envs(&self) -> Vec<(&str, &Path)> {
        let mut envs: Vec<(&str, &Path)> = vec![("GIT_INDEX_FILE", &self.index)];
        if let (Some(objects), Some(alternate)) = (&self.objects, &self.alternate) {
            envs.push(("GIT_OBJECT_DIRECTORY", objects));
            envs.push(("GIT_ALTERNATE_OBJECT_DIRECTORIES", alternate));
        }
        envs
    }
}

impl Drop for TempStore {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.index);
        if let Some(objects) = &self.objects {
            let _ = fs::remove_dir_all(objects);
        }
    }
}

/// Tree object of the working tree as git would commit it: untracked files included, ignored
/// files and the Stillwright state folder left out. The user's index is never touched. With
/// `keep_objects` false the objects go to a temp store that is deleted afterwards, so hashing
/// leaves nothing in the repository; a snapshot keeps them.
fn tree_of_worktree(top: &str, keep_objects: bool) -> Result<String> {
    let store = TempStore::new(top, keep_objects)?;
    stage_tree(top, &store)
}

/// Stage the working tree into the store's index and write it as a tree object.
fn stage_tree(top: &str, store: &TempStore) -> Result<String> {
    let envs = store.envs();
    let mut add = vec!["add", "-A", "--", "."];
    let exclude;
    if let Ok(state) = state_root().and_then(|s| fs::canonicalize(s).map_err(|e| e.to_string())) {
        if let Ok(top_real) = fs::canonicalize(top) {
            if let Ok(rel) = state.strip_prefix(&top_real) {
                exclude = format!(":(exclude){}", rel.to_string_lossy().replace('\\', "/"));
                add.push(&exclude);
            }
        }
    }
    git(Some(top), &envs, &add)
        .ok_or_else(|| {
            format!(
                "git could not read the working tree at {top} (`git add -A` failed: an unreadable file, permissions, or safe.directory?)"
            )
        })
        .and_then(|_| {
            git(Some(top), &envs, &["write-tree"]).ok_or_else(|| "git write-tree failed".to_string())
        })
}

/// Hash of the working tree; "none" outside a repository, an error when git fails inside one.
fn worktree_hash() -> Result<String> {
    match git_top() {
        Some(top) => tree_of_worktree(&top, false),
        None => Ok("none".into()),
    }
}

/// Commit the working tree as a snapshot under `refs/sw/<run>/<label>`; the user's branch,
/// index and HEAD are untouched. Returns the commit hash.
fn take_snapshot(top: &str, run: &Path, label: &str, message: &str) -> Result<String> {
    let tree = tree_of_worktree(top, true)?;
    let mut args = vec!["commit-tree", tree.as_str(), "-m", message];
    if git(Some(top), &[], &["rev-parse", "--verify", "-q", "HEAD"]).is_some() {
        args.extend(["-p", "HEAD"]);
    }
    // Snapshots have their own identity, so a machine without user.name/email still works.
    let who = Path::new("stillwright");
    let mail = Path::new("sw@stillwright.local");
    let identity = [
        ("GIT_AUTHOR_NAME", who),
        ("GIT_AUTHOR_EMAIL", mail),
        ("GIT_COMMITTER_NAME", who),
        ("GIT_COMMITTER_EMAIL", mail),
    ];
    let commit = git(Some(top), &identity, &args)
        .ok_or("git commit-tree failed (is git older than 2.13, or the repository read-only?)")?;
    let reference = snapshot_ref(run, label);
    git(Some(top), &[], &["update-ref", &reference, &commit])
        .ok_or_else(|| format!("cannot write {reference}"))?;
    Ok(commit)
}

fn snapshot_ref(run: &Path, label: &str) -> String {
    format!("refs/sw/{}/{label}", file_name(run))
}

/// `base`, or `base-2`, `base-3`… if that ref already exists: a snapshot never overwrites one.
fn free_label(top: &str, run: &Path, base: &str) -> String {
    let mut label = base.to_string();
    let mut n = 1;
    while git(
        Some(top),
        &[],
        &["rev-parse", "--verify", "-q", &snapshot_ref(run, &label)],
    )
    .is_some()
    {
        n += 1;
        label = format!("{base}-{n}");
    }
    label
}

fn run_snapshot(run: &Path, step: &str) -> Result<()> {
    let top = git_top().ok_or("a snapshot needs a git repository here")?;
    note_plan(run)?;
    let label = format!("step-{step}");
    let commit = take_snapshot(
        &top,
        run,
        &label,
        &format!("sw snapshot before step {step}"),
    )?;
    let mut event = serde_json::Map::new();
    event.insert("event".into(), "snapshot".into());
    event.insert("step".into(), step.into());
    event.insert("commit".into(), commit.clone().into());
    append_json(run, event)?;
    println!(
        "step {step}: snapshot {} saved at {}",
        short(&commit),
        snapshot_ref(run, &label)
    );
    Ok(())
}

/// Restore the files of a step's snapshot. Files that exist now but not in the snapshot are
/// removed unless git ignores them; the state being replaced is snapshotted first.
fn run_rewind(run: &Path, step: &str) -> Result<()> {
    let top = git_top().ok_or("a rewind needs a git repository here")?;
    let target = snapshot_ref(run, &format!("step-{step}"));
    let commit =
        git(Some(&top), &[], &["rev-parse", "--verify", "-q", &target]).ok_or_else(|| {
            format!("step {step}: no snapshot; `sw run done` and `sw run snapshot` take them")
        })?;
    let kept_label = free_label(
        &top,
        run,
        &format!("before-rewind-{}", now().replace([':', 'T'], "")),
    );
    let kept = take_snapshot(
        &top,
        run,
        &kept_label,
        &format!("sw state before rewinding to step {step}"),
    )?;
    let index = temp_git_path("index");
    let envs: [(&str, &Path); 1] = [("GIT_INDEX_FILE", &index)];
    let restored = git(Some(&top), &envs, &["read-tree", &commit])
        .and_then(|_| git(Some(&top), &envs, &["checkout-index", "-a", "-f"]))
        .and_then(|_| {
            git(
                Some(&top),
                &envs,
                &["ls-files", "-z", "--others", "--exclude-standard"],
            )
        });
    let _ = fs::remove_file(&index);
    let extra = restored.ok_or("git could not restore the snapshot")?;
    // Never remove the state folder when it lives inside the repository: it is not in the
    // snapshot, by design.
    let top_path = Path::new(&top);
    let state = state_root()
        .ok()
        .and_then(|s| fs::canonicalize(s).ok())
        .filter(|s| fs::canonicalize(top_path).is_ok_and(|t| s.starts_with(t)));
    let mut removed = 0;
    for rel in extra.split('\0').filter(|l| !l.is_empty()) {
        let path = top_path.join(rel);
        let in_state = match (&state, fs::canonicalize(&path)) {
            (Some(state), Ok(real)) => real.starts_with(state),
            _ => false,
        };
        if in_state || fs::remove_file(&path).is_err() {
            continue;
        }
        removed += 1;
        // Directories emptied by that removal go too, up to the repository root.
        let mut dir = path.parent();
        while let Some(d) = dir {
            if d == top_path || fs::remove_dir(d).is_err() {
                break;
            }
            dir = d.parent();
        }
    }
    let mut event = serde_json::Map::new();
    event.insert("event".into(), "rewind".into());
    event.insert("step".into(), step.into());
    event.insert("commit".into(), commit.clone().into());
    event.insert("kept".into(), kept.clone().into());
    event.insert("removed".into(), removed.into());
    append_json(run, event)?;
    println!(
        "step {step}: files restored from snapshot {} ({removed} newer files removed); the state before is kept at {}",
        short(&commit),
        snapshot_ref(run, &kept_label)
    );
    Ok(())
}

#[cfg(windows)]
fn shell(cmd: &str) -> Result<std::process::Output> {
    use std::os::windows::process::CommandExt;
    // raw_arg: cmd.exe has its own quoting, which the default escaping would break.
    // No pipefail on Windows: a failure inside a pipe is not caught there.
    Command::new("cmd")
        .raw_arg(format!("/C {cmd}"))
        .output()
        .map_err(|e| format!("cannot run the check: {e}"))
}

#[cfg(not(windows))]
fn shell(cmd: &str) -> Result<std::process::Output> {
    // bash for pipefail (a failing command inside a pipe must fail the check); sh if absent,
    // and then a pipe only reports its last command.
    let result = match Command::new("bash")
        .args(["-o", "pipefail", "-c", cmd])
        .output()
    {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
            Command::new("sh").args(["-c", cmd]).output()
        }
        other => other,
    };
    result.map_err(|e| format!("cannot run the check: {e}"))
}

/// Every event in the run's log. A missing log is empty; an unreadable one is an error, so a
/// freeze can never be skipped by making the log unreadable.
fn log_events(run: &Path) -> Result<Vec<serde_json::Map<String, serde_json::Value>>> {
    let text = match fs::read_to_string(run.join("log.jsonl")) {
        Ok(text) => text,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
        Err(e) => return Err(format!("cannot read {}/log.jsonl: {e}", file_name(run))),
    };
    Ok(text
        .lines()
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect())
}

fn event_is(event: &serde_json::Map<String, serde_json::Value>, key: &str, value: &str) -> bool {
    event.get(key).map(value_str).as_deref() == Some(value)
}

/// Frozen paths (absolute) and their hashes; a later freeze of a path replaces the earlier one.
fn frozen_files(run: &Path) -> Result<BTreeMap<String, String>> {
    let mut files = BTreeMap::new();
    for event in log_events(run)? {
        if !event_is(&event, "event", "freeze") {
            continue;
        }
        if let Some(serde_json::Value::Object(map)) = event.get("files") {
            for (path, hash) in map {
                files.insert(path.clone(), value_str(hash));
            }
        }
    }
    Ok(files)
}

/// Frozen paths whose content differs from the hash taken at freeze time (or that are gone).
fn tampered_paths(run: &Path) -> Result<Vec<String>> {
    Ok(frozen_files(run)?
        .iter()
        .filter(|(path, hash)| frozen_hash(Path::new(path)).ok().as_deref() != Some(hash))
        .map(|(path, _)| path.clone())
        .collect())
}

/// Hash of a frozen path's content; a symlink also hashes where it points, so retargeting
/// it shows up as tampering.
fn frozen_hash(path: &Path) -> Result<String> {
    let content = content_hash(path)?;
    match fs::read_link(path) {
        Ok(target) => Ok(format!(
            "{:x}",
            Sha256::digest(format!("{content} -> {}", target.to_string_lossy()))
        )),
        Err(_) => Ok(content),
    }
}

fn latest_receipt(
    run: &Path,
    step: &str,
) -> Result<Option<serde_json::Map<String, serde_json::Value>>> {
    Ok(log_events(run)?
        .into_iter()
        .rev()
        .find(|e| event_is(e, "event", "receipt") && event_is(e, "step", step)))
}

fn step_command(run: &Path, step: &str) -> Result<String> {
    let plan = fs::read_to_string(run.join("plan.md"))
        .map_err(|_| format!("{} has no plan.md yet", file_name(run)))?;
    let check =
        plan_step_check(&plan, step).ok_or_else(|| format!("step {step} is not in plan.md"))?;
    command_check(&check).map(str::to_string).ok_or_else(|| {
        format!(
            "step {step}'s check is not a command; write it as `check: $ <command>` so sw can run it"
        )
    })
}

fn run_check(run: &Path, step: &str) -> Result<()> {
    let cmd = step_command(run, step)?;
    note_plan(run)?;
    let mut event = serde_json::Map::new();
    event.insert("event".into(), "receipt".into());
    event.insert("step".into(), step.into());
    event.insert("cmd".into(), cmd.clone().into());
    event.insert("cwd".into(), current_dir()?.into());
    let tampered = tampered_paths(run)?;
    if !tampered.is_empty() {
        let list = tampered.join(", ");
        event.insert("tampered".into(), tampered.into());
        event.insert("result".into(), "fail".into());
        append_json(run, event)?;
        return Err(format!(
            "step {step}: tampered: {list} changed since it was frozen, so the check did not run. \
             If the change is intended, run `sw run freeze` again; the log keeps both."
        ));
    }
    let started = Instant::now();
    let output = shell(&cmd)?;
    let secs = started.elapsed().as_secs_f64();
    let code = output.status.code().unwrap_or(-1);
    let mut text = output.stdout;
    if !output.stderr.is_empty() {
        text.extend_from_slice(b"--- stderr ---\n");
        text.extend_from_slice(&output.stderr);
    }
    let checks = run.join("checks");
    fs::create_dir_all(&checks).map_err(|e| e.to_string())?;
    let stamp = now().replace([':', 'T'], "");
    let mut log_path = checks.join(format!("{step}-{stamp}.log"));
    let mut n = 1;
    while log_path.exists() {
        n += 1;
        log_path = checks.join(format!("{step}-{stamp}-{n}.log"));
    }
    fs::write(&log_path, &text).map_err(|e| format!("cannot write {}: {e}", log_path.display()))?;
    let tree = worktree_hash()?;
    event.insert("exit".into(), code.into());
    event.insert("ok".into(), (code == 0).into());
    event.insert("secs".into(), ((secs * 10.0).round() / 10.0).into());
    event.insert(
        "out_sha256".into(),
        format!("{:x}", Sha256::digest(&text)).into(),
    );
    event.insert("log".into(), file_name(&log_path).into());
    event.insert("tree".into(), tree.clone().into());
    if code != 0 {
        event.insert("result".into(), "fail".into());
    }
    append_json(run, event)?;
    if code == 0 {
        println!(
            "step {step}: check passed (exit 0, {secs:.1}s, tree {}); `sw run done` when the step's work is complete",
            short(&tree)
        );
        Ok(())
    } else {
        Err(format!(
            "step {step}: check failed (exit {code}); output in {}",
            log_path.display()
        ))
    }
}

fn current_dir() -> Result<String> {
    std::env::current_dir()
        .map(|d| d.to_string_lossy().into_owned())
        .map_err(|e| format!("cannot read the current directory: {e}"))
}

fn short(hash: &str) -> &str {
    if hash.len() > 12 {
        &hash[..12]
    } else {
        hash
    }
}

fn run_done(run: &Path, step: &str) -> Result<()> {
    let cmd = step_command(run, step)?;
    let receipt = latest_receipt(run, step)?
        .ok_or_else(|| format!("step {step}: no receipt; run `sw run check <run> {step}` first"))?;
    if receipt.get("ok") != Some(&serde_json::Value::Bool(true)) {
        return Err(format!(
            "step {step}: the last check failed or was tampered; fix it and run `sw run check` again"
        ));
    }
    let tampered = tampered_paths(run)?;
    if !tampered.is_empty() {
        return Err(format!(
            "step {step}: tampered: {} changed after the check; freeze again and run `sw run check`",
            tampered.join(", ")
        ));
    }
    let here = current_dir()?;
    let there = receipt.get("cwd").map(value_str).unwrap_or_default();
    if there != here {
        return Err(format!(
            "step {step}: the check ran in another directory ({there}); run `sw run done` from there, or check again here"
        ));
    }
    if git_top().is_none() {
        eprintln!(
            "warning: no git repository here, so the receipt is not tied to the files; anything may have changed since the check"
        );
    }
    let ran = receipt.get("cmd").map(value_str).unwrap_or_default();
    if ran != cmd {
        return Err(format!(
            "step {step}: the plan's check changed since the receipt (it ran `{ran}`, plan.md now says `{cmd}`); run `sw run check` again"
        ));
    }
    let then = receipt.get("tree").map(value_str).unwrap_or_default();
    let tree = worktree_hash()?;
    if then != tree {
        return Err(format!(
            "step {step}: stale receipt: the working tree changed since the check (was {}, now {}); run `sw run check` again",
            short(&then),
            short(&tree)
        ));
    }
    note_plan(run)?;
    let mut event = serde_json::Map::new();
    event.insert("step".into(), step.into());
    event.insert("result".into(), "pass".into());
    event.insert("certified".into(), true.into());
    event.insert("check".into(), cmd.clone().into());
    event.insert("tree".into(), tree.clone().into());
    if let Some(ts) = receipt.get("ts") {
        event.insert("receipt".into(), ts.clone());
    }
    if let Some(top) = git_top() {
        let label = format!("step-{step}");
        let commit = take_snapshot(
            &top,
            run,
            &label,
            &format!("sw snapshot at step {step} done"),
        )?;
        event.insert("snapshot".into(), commit.into());
    }
    append_json(run, event)?;
    println!(
        "step {step}: done, certified (`{cmd}` exit 0 on tree {})",
        short(&tree)
    );
    Ok(())
}

/// Keys only sw writes: hand-logging them would forge a receipt, a snapshot or a certificate.
const SW_KEYS: [&str; 16] = [
    "event",
    "ok",
    "log",
    "tree",
    "certified",
    "snapshot",
    "exit",
    "cmd",
    "cwd",
    "tampered",
    "secs",
    "out_sha256",
    "receipt",
    "commit",
    "evidence_sha256",
    "sha256",
];

fn plan_hash(run: &Path) -> Option<String> {
    fs::read(run.join("plan.md"))
        .ok()
        .map(|b| format!("{:x}", Sha256::digest(&b)))
}

/// Record the plan's hash the first time a step is worked on, so a later edit of plan.md is
/// visible to a reviewer.
fn note_plan(run: &Path) -> Result<()> {
    let Some(sha) = plan_hash(run) else {
        return Ok(());
    };
    if log_events(run)?
        .iter()
        .any(|e| event_is(e, "event", "plan"))
    {
        return Ok(());
    }
    let mut event = serde_json::Map::new();
    event.insert("event".into(), "plan".into());
    event.insert("sha256".into(), sha.into());
    append_json(run, event)
}

/// Evidence files behind hand-logged passes that are gone or changed since they were logged.
fn evidence_problems(run: &Path) -> Result<Vec<String>> {
    let mut latest: BTreeMap<String, (String, String)> = BTreeMap::new();
    for e in log_events(run)? {
        if let (Some(step), Some(path), Some(sha)) =
            (e.get("step"), e.get("evidence"), e.get("evidence_sha256"))
        {
            if event_is(&e, "result", "pass") {
                latest.insert(value_str(step), (value_str(path), value_str(sha)));
            }
        }
    }
    let mut problems = Vec::new();
    for (step, (path, sha)) in latest {
        match fs::read(&path) {
            Err(_) => problems.push(format!("step {step}: evidence missing ({path})")),
            Ok(bytes) if format!("{:x}", Sha256::digest(&bytes)) != sha => problems.push(format!(
                "step {step}: evidence changed since it was logged ({path})"
            )),
            Ok(_) => {}
        }
    }
    Ok(problems)
}

/// `fs::canonicalize` on Windows returns a `\\?\C:\…` verbatim path; the plain form is what
/// users and other tools write.
fn plain_path(path: PathBuf) -> PathBuf {
    let text = path.to_string_lossy();
    match text.strip_prefix(r"\\?\") {
        Some(rest) if cfg!(windows) && !rest.starts_with("UNC\\") => PathBuf::from(rest),
        _ => path,
    }
}

/// A pass on a step no command can check must point at evidence: a non-empty file (the
/// reviewer's verdict, a screenshot, the fetched page) outside the run folder, or under its
/// `checks/`. The path is stored canonical with the file's sha256, so the claim and what backed
/// it can be opened together later, and `sw run status` notices when it is gone or changed.
fn with_evidence(
    pairs: Vec<(String, String)>,
    dir: &Path,
    run: &str,
    step: &str,
) -> Result<Vec<(String, String)>> {
    let given = pairs
        .iter()
        .find(|(k, _)| k == "evidence")
        .map(|(_, v)| v.trim().to_string())
        .filter(|v| !v.is_empty())
        .ok_or_else(|| {
            format!(
                "step {step} has no command check, so a pass needs evidence=<file> (the reviewer's \
                 verdict, a screenshot, the fetched page). `sw run review {run} {step}` prints what a \
                 fresh reviewer should see and where to write the verdict."
            )
        })?;
    let path = plain_path(
        fs::canonicalize(&given)
            .map_err(|_| format!("evidence file not found: {given} (step {step})"))?,
    );
    if !path.is_file() {
        return Err(format!("evidence must be a file: {}", path.display()));
    }
    if let Ok(run_dir) = fs::canonicalize(dir) {
        if path.starts_with(&run_dir) && !path.starts_with(run_dir.join("checks")) {
            return Err(format!(
                "evidence cannot be one of the run folder's own files ({}); write the verdict under {}",
                path.display(),
                run_dir.join("checks").display()
            ));
        }
    }
    let bytes = fs::read(&path).map_err(|e| format!("cannot read {}: {e}", path.display()))?;
    if bytes.iter().all(u8::is_ascii_whitespace) {
        return Err(format!("evidence file is empty: {}", path.display()));
    }
    let sha = format!("{:x}", Sha256::digest(&bytes));
    let mut out: Vec<(String, String)> = pairs
        .into_iter()
        .filter(|(k, _)| k != "evidence" && k != "evidence_sha256")
        .collect();
    out.push(("evidence".into(), path.to_string_lossy().into_owned()));
    out.push(("evidence_sha256".into(), sha));
    Ok(out)
}

/// The most lines a section of the review packet may take; the rest is counted, not shown.
const PACKET_LINES: usize = 400;

const PACKET_LINE_CHARS: usize = 2000;
const PACKET_BYTES: usize = 64 * 1024;

/// At most `max` lines, each at most PACKET_LINE_CHARS, the whole at most PACKET_BYTES.
fn clip_lines(text: &str, max: usize) -> String {
    let total = text.lines().count();
    let cut_line = |line: &str| -> String {
        match line.char_indices().nth(PACKET_LINE_CHARS) {
            Some((i, _)) => format!("{}… (line cut)", &line[..i]),
            None => line.to_string(),
        }
    };
    let shown: Vec<String> = text.lines().take(max).map(cut_line).collect();
    let mut out = shown.join("\n").trim_end().to_string();
    if total > max {
        out.push_str(&format!("\n… {} more lines", total - max));
    }
    if out.len() > PACKET_BYTES {
        let mut end = PACKET_BYTES;
        while !out.is_char_boundary(end) {
            end -= 1;
        }
        out.truncate(end);
        out.push_str("\n… cut at 64 KiB");
    }
    out
}

/// The base a reviewer should diff against: the snapshot taken before this step
/// (`sw run snapshot`), else the snapshot of the newest certified step before it.
fn review_base(top: &str, run: &Path, step: &str) -> Option<(String, String)> {
    let this: u64 = step.parse().ok()?;
    let events = log_events(run).ok()?;
    let exists = |commit: &str| {
        git(
            Some(top),
            &[],
            &[
                "rev-parse",
                "--verify",
                "-q",
                &format!("{commit}^{{commit}}"),
            ],
        )
        .is_some()
    };
    let before = events
        .iter()
        .rev()
        .find(|e| event_is(e, "event", "snapshot") && event_is(e, "step", step))
        .and_then(|e| e.get("commit").map(value_str))
        .filter(|c| exists(c));
    if let Some(commit) = before {
        return Some((format!("the snapshot before step {step}"), commit));
    }
    events
        .iter()
        .filter(|e| e.get("certified") == Some(&serde_json::Value::Bool(true)))
        .filter_map(|e| {
            let k: u64 = e.get("step").map(value_str)?.parse().ok()?;
            let commit = e.get("snapshot").map(value_str)?;
            (k < this && exists(&commit)).then_some((k, commit))
        })
        .max_by_key(|(k, _)| *k)
        .map(|(k, commit)| (format!("step {k}"), commit))
}

/// Paths in a diff that are nested repositories: their own changes are not in the diff.
fn nested_repos(diff: &str) -> Vec<String> {
    let mut current = String::new();
    let mut found = Vec::new();
    for line in diff.lines() {
        if let Some(rest) = line.strip_prefix("diff --git a/") {
            current = rest.split(" b/").next().unwrap_or("").to_string();
        } else if (line.starts_with("+Subproject commit") || line.starts_with("-Subproject commit"))
            && !found.contains(&current)
        {
            found.push(current.clone());
        }
    }
    found
}

/// The diff a reviewer should read: the last snapshot before this step (or HEAD) against the
/// working tree as it is now, untracked files included, the state folder left out.
fn print_changes(top: &str, run: &Path, step: &str) -> Result<()> {
    let (label, base) = match review_base(top, run, step) {
        Some(base) => base,
        None => match git(Some(top), &[], &["rev-parse", "--verify", "-q", "HEAD"]) {
            Some(head) => ("HEAD".to_string(), head),
            None => {
                // No commit yet: diff against the empty tree (write-tree on a missing index).
                let index = temp_git_path("empty-index");
                let empty = git(Some(top), &[("GIT_INDEX_FILE", &index)], &["write-tree"])
                    .ok_or("git write-tree failed")?;
                ("an empty repository".to_string(), empty)
            }
        },
    };
    // The current tree goes to a temp store, so a review writes nothing into .git/objects.
    let store = TempStore::new(top, false)?;
    let now = stage_tree(top, &store)?;
    let diff = git(
        Some(top),
        &store.envs(),
        &[
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--stat=80",
            "-p",
            &base,
            &now,
        ],
    )
    .ok_or_else(|| format!("git diff {} failed", short(&base)))?;
    println!("\nChanges since {label} (tracked and new files, ignored files left out):");
    if diff.trim().is_empty() {
        println!("(none)");
    } else {
        println!("{}", clip_lines(&diff, PACKET_LINES));
    }
    for path in nested_repos(&diff) {
        println!("nested repository {path}: its own changes are not shown; open it");
    }
    Ok(())
}

/// The review packet: what a fresh reviewer may see. The plan's goal and constraints, the step
/// and its check, the changes since the last snapshot, the latest check output. What the worker
/// wrote about the step (its notes, its result) is left out on purpose.
fn run_review(run: &Path, step: &str) -> Result<()> {
    let plan = fs::read_to_string(run.join("plan.md"))
        .map_err(|_| format!("{} has no plan.md yet", file_name(run)))?;
    let line =
        plan_step_line(&plan, step).ok_or_else(|| format!("step {step} is not in plan.md"))?;
    let check = plan_step_check(&plan, step).unwrap_or_else(|| "(none in the plan)".to_string());
    println!("Review packet: step {step} of {}", file_name(run));
    println!("What the worker said about this step is left out on purpose; judge the work.");
    let recorded = log_events(run)?
        .iter()
        .find(|e| event_is(e, "event", "plan"))
        .and_then(|e| e.get("sha256").map(value_str));
    if recorded.is_some() && recorded != plan_hash(run) {
        println!(
            "Note: plan.md changed since the first step was logged; its lines are the worker's text, and the check may not be the one the step was planned with."
        );
    }
    for l in plan.lines().map(str::trim) {
        if let Some(goal) = l.strip_prefix("# Goal:") {
            println!("Goal: {}", goal.trim());
        } else if l.to_lowercase().starts_with("must not:")
            || l.to_lowercase().starts_with("never:")
            || l.starts_with("Outward:")
        {
            println!("{l}");
        }
    }
    println!("Step {step}: {line}");
    println!("Check: {check}");
    match git_top() {
        Some(top) => print_changes(&top, run, step)?,
        None => println!(
            "\nChanges: no git repository here, so there is no diff; open the files the step names."
        ),
    }
    if let Some(receipt) = latest_receipt(run, step)? {
        let name = receipt.get("log").map(value_str).unwrap_or_default();
        let cmd = receipt.get("cmd").map(value_str).unwrap_or_default();
        let bare = !name.is_empty() && !name.contains(['/', '\\']) && name != "..";
        let genuine = matches!(receipt.get("ok"), Some(serde_json::Value::Bool(_)));
        if bare && genuine && command_check(&check) == Some(cmd.as_str()) {
            let text = fs::read_to_string(run.join("checks").join(&name))
                .unwrap_or_else(|_| "(output file missing)".to_string());
            println!(
                "\nLatest check output (`{cmd}`, exit {}):",
                receipt.get("exit").map(value_str).unwrap_or_default()
            );
            println!("{}", clip_lines(&text, PACKET_LINES / 4));
        } else {
            println!(
                "\nThe latest check receipt for step {step} is stale (the plan's check is not what it ran) and is not shown."
            );
        }
    }
    let checks = run.join("checks");
    fs::create_dir_all(&checks).map_err(|e| format!("cannot create {}: {e}", checks.display()))?;
    let verdict = checks.join(format!("step-{step}-review.md"));
    println!(
        "\nStart from FAIL. Pass only what the changes and the output prove; list each requirement \
         of the check as pass or fail with the evidence. Write the verdict to {} and log it with \
         `sw run log {} step={step} result=pass|fail evidence=\"{}\"`.",
        verdict.display(),
        file_name(run),
        verdict.display()
    );
    Ok(())
}

/// The full line of one step, without its number.
fn plan_step_line(plan: &str, step: &str) -> Option<String> {
    plan.lines().find_map(|line| {
        let digits: String = line.chars().take_while(|c| c.is_ascii_digit()).collect();
        let rest = &line[digits.len()..];
        (digits == step && rest.starts_with('.')).then(|| rest[1..].trim().to_string())
    })
}

/// The step numbers listed in a step's `after:` field (`-` or none means no dependencies).
fn step_after(plan: &str, step: &str) -> Vec<String> {
    plan_step_line(plan, step)
        .and_then(|line| {
            line.split('|').find_map(|part| {
                part.trim_start()
                    .strip_prefix("after:")
                    .map(|a| a.trim().to_string())
            })
        })
        .map(|after| {
            after
                .split(|c: char| c == ',' || c.is_whitespace())
                .filter(|s| !s.is_empty() && *s != "-")
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default()
}

/// Steps not yet passed whose dependencies all passed.
fn runnable_steps(plan: &str, results: &BTreeMap<String, String>) -> Vec<String> {
    let passed = |s: &str| results.get(s).map(String::as_str) == Some("pass");
    plan_steps(plan)
        .into_iter()
        .filter(|s| !passed(s))
        .filter(|s| step_after(plan, s).iter().all(|d| passed(d)))
        .collect()
}

/// What must survive a compaction: goal, must-nots, outward line, the next step and its check.
/// The folder a run was started from, recorded by `sw run new`.
fn run_cwd(run: &Path) -> Option<String> {
    log_events(run)
        .ok()?
        .into_iter()
        .find(|e| event_is(e, "event", "start"))
        .and_then(|e| e.get("cwd").map(value_str))
}

fn run_brief(store: &Store) -> Result<()> {
    // The newest open run started in this folder (or a parent or child of it): a run from
    // another project must not leak into this session's context.
    let here = std::env::current_dir()
        .ok()
        .and_then(|d| fs::canonicalize(d).ok())
        .map(|d| d.to_string_lossy().into_owned())
        .unwrap_or_default();
    let open = store.runs()?.into_iter().rev().find(|dir| {
        let same_place = run_cwd(dir).is_some_and(|c| here.starts_with(&c) || c.starts_with(&here));
        same_place && Progress::of(dir).next.is_some()
    });
    let Some(dir) = open else {
        return Ok(());
    };
    let plan = fs::read_to_string(dir.join("plan.md")).unwrap_or_default();
    let progress = Progress::of(&dir);
    let Some(next) = progress.next.clone() else {
        return Ok(());
    };
    let clip = |s: &str| -> String {
        let mut t: String = s.chars().take(240).collect();
        if t.len() < s.len() {
            t.push('…');
        }
        t
    };
    println!(
        "Stillwright run {} ({}/{} steps passed)",
        file_name(&dir),
        progress.passed(),
        progress.total()
    );
    let mut lines = 0;
    for line in plan.lines() {
        let l = line.trim();
        if lines >= 8 {
            break;
        }
        if let Some(goal) = l.strip_prefix("# Goal:") {
            println!("Goal: {}", clip(goal.trim()));
            lines += 1;
        } else if l.to_lowercase().starts_with("must not:")
            || l.to_lowercase().starts_with("never:")
            || l.starts_with("Outward:")
        {
            println!("{}", clip(l));
            lines += 1;
        }
    }
    if let Some(line) = plan_step_line(&plan, &next) {
        println!("Next: step {next}: {}", clip(&line));
    }
    if plan_step_check(&plan, &next)
        .as_deref()
        .and_then(command_check)
        .is_some()
    {
        println!("Prove it with `sw run check latest {next}` then `sw run done latest {next}`; a pass by hand is refused.");
    }
    Ok(())
}

fn run_freeze(run: &Path, paths: &[String]) -> Result<()> {
    let mut files = serde_json::Map::new();
    for path in paths {
        // Absolute, so the check compares the same files from any directory; not resolved,
        // so a frozen symlink stays the link itself and retargeting it is caught.
        let full = std::path::absolute(path).map_err(|e| format!("cannot freeze {path}: {e}"))?;
        let hash = frozen_hash(&full).map_err(|e| format!("cannot freeze {path}: {e}"))?;
        files.insert(full.to_string_lossy().into_owned(), hash.into());
    }
    let mut event = serde_json::Map::new();
    event.insert("event".into(), "freeze".into());
    event.insert("files".into(), files.into());
    append_json(run, event)?;
    println!(
        "frozen: {}; any change fails the step's check until frozen again",
        paths.join(", ")
    );
    Ok(())
}

fn slugify(text: &str) -> String {
    let mut slug = String::new();
    for c in text.to_lowercase().chars() {
        if c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-' {
            slug.push(c);
        } else if !slug.ends_with('-') {
            slug.push('-');
        }
    }
    let slug: String = slug.trim_matches('-').chars().take(40).collect();
    let slug = slug.trim_end_matches('-').to_string();
    if slug.is_empty() {
        "run".into()
    } else {
        slug
    }
}

// ---------------------------------------------------------------- tools

fn content_hash(path: &Path) -> Result<String> {
    let mut files = Vec::new();
    if path.is_file() {
        files.push((file_name(path), path.to_path_buf()));
    } else {
        collect_files(path, path, &mut files)?;
        files.sort();
    }
    let mut digest = Sha256::new();
    for (rel, file) in files {
        let bytes = if file.as_os_str().is_empty() {
            Vec::new()
        } else {
            fs::read(&file).map_err(|e| format!("cannot read {}: {e}", file.display()))?
        };
        digest.update(rel.as_bytes());
        digest.update([0u8]);
        digest.update(&bytes);
        digest.update([0u8]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn rel_path(root: &Path, path: &Path) -> String {
    path.strip_prefix(root)
        .unwrap_or(path)
        .components()
        .map(|c| c.as_os_str().to_string_lossy().into_owned())
        .collect::<Vec<_>>()
        .join("/")
}

fn collect_files(root: &Path, dir: &Path, out: &mut Vec<(String, PathBuf)>) -> Result<()> {
    for entry in fs::read_dir(dir).map_err(|e| format!("cannot read {}: {e}", dir.display()))? {
        let path = entry.map_err(|e| e.to_string())?.path();
        if HASH_SKIP.contains(&file_name(&path).as_str()) {
            continue;
        }
        // Symlinks are hashed by their target path, never followed: following them can loop
        // forever (pnpm-style node_modules) or pull in files outside the tool.
        let meta = fs::symlink_metadata(&path)
            .map_err(|e| format!("cannot stat {}: {e}", path.display()))?;
        if meta.file_type().is_symlink() {
            let target = fs::read_link(&path).map_err(|e| e.to_string())?;
            out.push((
                rel_path(root, &path) + " -> " + &target.to_string_lossy(),
                PathBuf::new(),
            ));
        } else if meta.is_dir() {
            collect_files(root, &path, out)?;
        } else if meta.is_file() {
            let rel = path.strip_prefix(root).unwrap_or(&path);
            let rel = rel
                .components()
                .map(|c| c.as_os_str().to_string_lossy())
                .collect::<Vec<_>>()
                .join("/");
            out.push((rel, path));
        }
    }
    Ok(())
}

// ---------------------------------------------------------------- cache

struct Turn {
    ts: String,
    model: String,
    input: f64,
    created: f64,
    read: f64,
    output: f64,
}

/// A cache "break" is a turn that had to write a large prefix again instead of reading it.
/// The threshold is a heuristic: at least 5K tokens written and at least a quarter of what the
/// previous turn read, so normal growth (the new turn's own text) is not reported.
fn cache_report(store: &Store, file: &Path) -> Result<()> {
    let text =
        fs::read_to_string(file).map_err(|e| format!("cannot read {}: {e}", file.display()))?;
    let mut seen = std::collections::HashSet::new();
    let mut turns: Vec<Turn> = Vec::new();
    for line in text.lines() {
        let Ok(e) = serde_json::from_str::<serde_json::Value>(line) else {
            continue;
        };
        if e.get("type").and_then(|v| v.as_str()) != Some("assistant") {
            continue;
        }
        let Some(msg) = e.get("message") else {
            continue;
        };
        let Some(usage) = msg.get("usage") else {
            continue;
        };
        let id = msg
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        if !id.is_empty() && !seen.insert(id) {
            continue; // the same API response is logged once per content block
        }
        let num = |k: &str| usage.get(k).and_then(|v| v.as_f64()).unwrap_or(0.0);
        turns.push(Turn {
            ts: e
                .get("timestamp")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .chars()
                .take(19)
                .collect(),
            model: msg
                .get("model")
                .and_then(|v| v.as_str())
                .unwrap_or("?")
                .to_string(),
            input: num("input_tokens"),
            created: num("cache_creation_input_tokens"),
            read: num("cache_read_input_tokens"),
            output: num("output_tokens"),
        });
    }
    if turns.is_empty() {
        return Err("no assistant turns with usage found in that file".into());
    }
    let (mut input, mut created, mut read, mut output) = (0.0, 0.0, 0.0, 0.0);
    for t in &turns {
        input += t.input;
        created += t.created;
        read += t.read;
        output += t.output;
    }
    let prefix = input + created + read;
    let hit = if prefix > 0.0 {
        100.0 * read / prefix
    } else {
        0.0
    };
    println!(
        "{} turns | prefix tokens: read {:.0} ({hit:.0}% cached), written {:.0}, uncached {:.0} | output {:.0}",
        turns.len(),
        read,
        created,
        input,
        output
    );
    let mut breaks = 0;
    let mut wasted = 0.0;
    for i in 1..turns.len() {
        let (prev, cur) = (&turns[i - 1], &turns[i]);
        let big = cur.created >= 5000.0 && cur.created >= prev.read * 0.25;
        if !big {
            continue;
        }
        breaks += 1;
        wasted += cur.created;
        let gap_min = minutes_between(&prev.ts, &cur.ts);
        let cause = if cur.model != prev.model {
            format!("model switched {} -> {}", prev.model, cur.model)
        } else if gap_min >= 60.0 {
            format!("the cache expired during a {:.0}-minute pause", gap_min)
        } else if prev.read > 0.0 && cur.read < prev.read * 0.5 {
            "prefix changed: compaction, a settings/hook/MCP change, or an edited system prompt"
                .to_string()
        } else {
            "large new content entered the prefix (tool output or a long message)".to_string()
        };
        println!(
            "turn {}: {} wrote {:.0} tokens (read {:.0} -> {:.0}): likely {cause}",
            i + 1,
            cur.ts,
            cur.created,
            prev.read,
            cur.read
        );
    }
    if breaks == 0 {
        println!("no cache breaks found");
    } else {
        println!("{breaks} cache break(s), {wasted:.0} tokens rewritten");
        // A 5-minute cache write costs 1.25x the input price; a read costs the model's
        // cache-read price (a tenth of input when prices.json does not say). The difference is
        // an upper bound on the waste: content that was genuinely new could never have been a read.
        let prices_path = store.root.join("prices.json");
        if let Ok(text) = fs::read_to_string(&prices_path) {
            if let Ok(prices) = serde_json::from_str::<BTreeMap<String, Price>>(&text) {
                let model = &turns[0].model;
                if let Some(p) = lookup(&prices, model) {
                    let read = p.read.unwrap_or(p.input * 0.1);
                    let usd = wasted * (1.25 * p.input - read) / 1_000_000.0;
                    println!("at most about ${usd:.4} above cache-read price for those rewrites ({model})");
                }
            }
        }
    }
    Ok(())
}

/// Minutes between two ISO timestamps like 2026-10-26T10:00:00; 0 when either is unreadable.
fn minutes_between(a: &str, b: &str) -> f64 {
    let parse = |s: &str| {
        s.get(..19)
            .and_then(|head| chrono::NaiveDateTime::parse_from_str(head, "%Y-%m-%dT%H:%M:%S").ok())
    };
    match (parse(a), parse(b)) {
        (Some(x), Some(y)) => (y - x).num_seconds() as f64 / 60.0,
        _ => 0.0,
    }
}

// ---------------------------------------------------------------- init

const MARKETPLACE: &str = "stillwright";
const MARKETPLACE_REPO: &str = "HamzaIlyas/stillwright";

/// Merge the two plugin keys into a settings file, keeping everything else in it.
/// Both Claude Code (.claude/settings.json) and GitHub Copilot (.github/copilot/settings.json)
/// read `extraKnownMarketplaces` and `enabledPlugins` in this shape.
fn enable_in_settings(path: &Path) -> Result<bool> {
    let mut root: serde_json::Value = match fs::read_to_string(path) {
        Ok(text) if text.trim().is_empty() => serde_json::json!({}),
        Ok(text) => serde_json::from_str(text.trim_start_matches('\u{feff}')).map_err(|e| {
            format!(
                "{} is not valid JSON ({e}); fix it, then retry",
                path.display()
            )
        })?,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => serde_json::json!({}),
        Err(e) => return Err(format!("cannot read {}: {e}", path.display())),
    };
    if !root.is_object() {
        return Err(format!("{} must hold a JSON object", path.display()));
    }
    let before = root.clone();
    let obj = root.as_object_mut().expect("checked above");
    let markets = obj
        .entry("extraKnownMarketplaces")
        .or_insert_with(|| serde_json::json!({}));
    if !markets.is_object() {
        return Err(format!(
            "{}: extraKnownMarketplaces is not an object",
            path.display()
        ));
    }
    markets
        .as_object_mut()
        .expect("checked")
        .entry(MARKETPLACE)
        .or_insert_with(
            || serde_json::json!({ "source": { "source": "github", "repo": MARKETPLACE_REPO } }),
        );
    let plugins = obj
        .entry("enabledPlugins")
        .or_insert_with(|| serde_json::json!({}));
    if !plugins.is_object() {
        return Err(format!(
            "{}: enabledPlugins is not an object",
            path.display()
        ));
    }
    let key = format!("{MARKETPLACE}@{MARKETPLACE}");
    let plugins = plugins.as_object_mut().expect("checked");
    if plugins.get(&key) == Some(&serde_json::Value::Bool(false)) {
        // Someone turned it off here on purpose; init never overrides that.
        println!("{}: {key} is false, left as is", path.display());
    } else {
        plugins.insert(key, serde_json::Value::Bool(true));
    }
    if path.ends_with(Path::new(".claude").join("settings.json")) {
        // Claude Code hooks: the gate before every shell command, the brief after compaction.
        let hooks = obj.entry("hooks").or_insert_with(|| serde_json::json!({}));
        if !hooks.is_object() {
            return Err(format!("{}: hooks is not an object", path.display()));
        }
        let hooks = hooks.as_object_mut().expect("checked");
        for (event, matcher, command) in [
            ("PreToolUse", "Bash", "sw gate --hook"),
            ("SessionStart", "startup|resume|compact", "sw run brief"),
        ] {
            let list = hooks.entry(event).or_insert_with(|| serde_json::json!([]));
            let Some(list) = list.as_array_mut() else {
                return Err(format!("{}: hooks.{event} is not a list", path.display()));
            };
            let present = list.iter().any(|entry| {
                entry
                    .pointer("/hooks")
                    .and_then(|h| h.as_array())
                    .is_some_and(|h| {
                        h.iter()
                            .any(|x| x.get("command").and_then(|c| c.as_str()) == Some(command))
                    })
            });
            if !present {
                list.push(serde_json::json!({
                    "matcher": matcher,
                    "hooks": [{ "type": "command", "command": command, "timeout": 20 }]
                }));
            }
        }
    }
    if root == before {
        return Ok(false);
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|e| format!("cannot create {}: {e}", parent.display()))?;
    }
    let text = serde_json::to_string_pretty(&root).map_err(|e| e.to_string())? + "\n";
    fs::write(path, text).map_err(|e| format!("cannot write {}: {e}", path.display()))?;
    Ok(true)
}

fn init(args: InitArgs) -> Result<()> {
    if !args.dir.is_dir() {
        return Err(format!("{} is not a folder", args.dir.display()));
    }
    let both = !args.claude_only && !args.copilot_only;
    let mut targets: Vec<(&str, PathBuf)> = Vec::new();
    if both || args.claude_only {
        targets.push((
            "Claude Code",
            args.dir.join(".claude").join("settings.json"),
        ));
    }
    if both || args.copilot_only {
        targets.push((
            "GitHub Copilot",
            args.dir
                .join(".github")
                .join("copilot")
                .join("settings.json"),
        ));
    }
    for (name, path) in targets {
        let changed = enable_in_settings(&path)?;
        println!(
            "{name}: {} {}",
            if changed { "updated" } else { "already set" },
            path.display()
        );
    }
    println!("Commit these files. Contributors get Stillwright once they trust the folder (Claude Code) or open it (Copilot).");
    Ok(())
}

// ---------------------------------------------------------------- commands

fn gate_cmd(args: GateArgs) -> Result<()> {
    let (command, workspace) = if args.hook {
        let mut input = String::new();
        std::io::stdin()
            .read_to_string(&mut input)
            .map_err(|e| format!("cannot read the hook event: {e}"))?;
        let input = input.trim_start_matches('\u{feff}');
        let event: serde_json::Value = serde_json::from_str(input).unwrap_or_default();
        let Some(command) = event
            .pointer("/tool_input/command")
            .and_then(|v| v.as_str())
            .map(str::to_string)
        else {
            // Fail open: a PreToolUse hook that errors would block every command, and a
            // broken event is the host's bug; say so where the log can see it.
            eprintln!("warning: sw gate --hook: no tool_input.command in the event; allowed");
            return Ok(());
        };
        let cwd = event.get("cwd").and_then(|v| v.as_str()).map(PathBuf::from);
        (command, args.workspace.or(cwd))
    } else {
        // Re-quote words with spaces so `sw gate -- bash -c "rm -rf x"` is judged as typed.
        let line = args
            .command
            .iter()
            .map(|w| {
                if w.chars()
                    .any(|c| c.is_whitespace() || c == '"' || c == '\'')
                {
                    format!("'{}'", w.replace('\'', "'\\''"))
                } else {
                    w.clone()
                }
            })
            .collect::<Vec<_>>()
            .join(" ");
        (line, args.workspace)
    };
    // Where the command runs, and what it may touch: the repository the directory is in,
    // or the directory itself outside git. `--workspace` overrides.
    let cwd = match &workspace {
        Some(w) => w.clone(),
        None => std::env::current_dir().map_err(|e| e.to_string())?,
    };
    let workspace = match workspace {
        Some(w) => w,
        None => Command::new("git")
            .args(["rev-parse", "--show-toplevel"])
            .current_dir(&cwd)
            .output()
            .ok()
            .filter(|o| o.status.success())
            .map(|o| PathBuf::from(String::from_utf8_lossy(&o.stdout).trim()))
            .unwrap_or_else(|| cwd.clone()),
    };
    // The user's own rules: the state folder's guards.md, then the workspace's.
    let mut guards = Vec::new();
    let mut files = vec![workspace.join(".stillwright").join("guards.md")];
    if let Ok(root) = state_root() {
        files.insert(0, root.join("guards.md"));
    }
    for file in files {
        if let Ok(text) = fs::read_to_string(&file) {
            guards.extend(gate::parse_guards(&text));
        }
    }
    let decision = gate::judge_with_guards(&command, &workspace, &cwd, &guards);
    if args.hook {
        // Only destructive commands get a word; everything else stays silent and allowed.
        let permission = match decision.verdict {
            gate::Verdict::Allow => return Ok(()),
            gate::Verdict::Ask => "ask",
            gate::Verdict::Block => "deny",
        };
        let out = serde_json::json!({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": permission,
                "permissionDecisionReason": format!("stillwright gate: {}", gate::report(&decision).trim()),
            }
        });
        println!("{out}");
        return Ok(());
    }
    if args.json {
        println!(
            "{}",
            serde_json::to_string_pretty(&decision).map_err(|e| e.to_string())?
        );
    } else {
        print!("{}", gate::report(&decision));
    }
    if decision.verdict == gate::Verdict::Allow {
        Ok(())
    } else {
        std::process::exit(decision.verdict.exit_code().into());
    }
}

fn run(cli: Cli) -> Result<()> {
    if let Cmd::Gate(args) = cli.cmd {
        // Runs on every shell command when wired as a hook: no state folder, no lock.
        return gate_cmd(args);
    }
    let store = Store::open()?;
    let _lock = store.lock()?;
    match cli.cmd {
        Cmd::Status => status(&store),
        Cmd::Home => {
            println!("{}", store.root.display());
            Ok(())
        }
        Cmd::Goal(cmd) => goal(&store, cmd),
        Cmd::Run(cmd) => run_cmd(&store, cmd),
        Cmd::Inbox(cmd) => inbox(&store, cmd),
        Cmd::Note(cmd) => note(&store, cmd),
        Cmd::Tool(cmd) => tool(&store, cmd),
        Cmd::Init(args) => init(args),
        Cmd::Cache { file } => cache_report(&store, &file),
        Cmd::Gate(_) => unreachable!("handled before the store opens"),
        Cmd::Route { who } => route(&store, &who),
        Cmd::Lesson(cmd) => lesson(&store, cmd),
    }
}

// ---------------------------------------------------------------- stats and routing

struct RouteStat {
    steps: usize,
    passed: usize,
    dollars: f64,
    priced: bool,
}

/// Per (who, model) across all runs: steps, passes and dollars, from logged step events.
fn route_stats(store: &Store) -> Result<BTreeMap<(String, String), RouteStat>> {
    let prices: BTreeMap<String, Price> = match fs::read_to_string(store.root.join("prices.json")) {
        Ok(text) => {
            serde_json::from_str(&text).map_err(|e| format!("prices.json is not valid ({e})"))?
        }
        Err(_) => BTreeMap::new(),
    };
    let mut stats: BTreeMap<(String, String), RouteStat> = BTreeMap::new();
    for run in store.runs()? {
        // One row per step, from every event about it: a certified `done`, a cost line and a
        // retry all describe the same step. Steps with no result yet are left out.
        let plan = fs::read_to_string(run.join("plan.md")).unwrap_or_default();
        #[allow(clippy::type_complexity)]
        let mut steps: BTreeMap<
            String,
            (
                Option<String>,
                Option<String>,
                f64,
                f64,
                bool,
                Option<String>,
            ),
        > = BTreeMap::new();
        for e in log_events(&run)? {
            let Some(step) = e.get("step").map(value_str) else {
                continue;
            };
            let entry = steps
                .entry(step.clone())
                .or_insert((None, None, 0.0, 0.0, false, None));
            if let Some(who) = e.get("who").map(value_str) {
                entry.0 = Some(who);
            }
            if let Some(model) = e.get("model").map(value_str) {
                entry.1 = Some(model);
            }
            let num = |k: &str| e.get(k).map(value_str).and_then(|v| v.parse::<f64>().ok());
            if let (Some(i), Some(o)) = (num("in"), num("out")) {
                entry.2 += i;
                entry.3 += o;
                entry.4 = true;
            }
            if let Some(result) = e.get("result").map(value_str) {
                entry.5 = Some(result);
            }
        }
        for (step, (who, model, input, output, tokens_logged, result)) in steps {
            let Some(result) = result else { continue };
            let who = who
                .or_else(|| {
                    plan_step_line(&plan, &step).and_then(|l| {
                        l.split('|').find_map(|p| {
                            p.trim_start()
                                .strip_prefix("who:")
                                .map(|w| w.trim().to_string())
                        })
                    })
                })
                .unwrap_or_else(|| "(no route)".into());
            let model = model.unwrap_or_else(|| "(no model logged)".into());
            let stat = stats.entry((who, model.clone())).or_insert(RouteStat {
                steps: 0,
                passed: 0,
                dollars: 0.0,
                priced: true,
            });
            stat.steps += 1;
            if result == "pass" {
                stat.passed += 1;
            }
            match lookup(&prices, &model) {
                Some(p) if tokens_logged => {
                    stat.dollars += (input * p.input + output * p.output) / 1_000_000.0
                }
                _ => stat.priced = false,
            }
        }
    }
    Ok(stats)
}

fn run_stats(store: &Store) -> Result<()> {
    let stats = route_stats(store)?;
    if stats.is_empty() {
        println!("no step results logged with who= and model= yet");
        return Ok(());
    }
    for ((who, model), s) in &stats {
        let rate = (100 * s.passed).checked_div(s.steps).unwrap_or(0);
        let per = if s.priced && s.passed > 0 {
            format!("${:.4} per passed step", s.dollars / s.passed as f64)
        } else if !s.priced {
            "no price in prices.json".to_string()
        } else {
            "nothing passed yet".to_string()
        };
        println!(
            "{who} {model}: {} steps, {} passed ({rate}%), {per}",
            s.steps, s.passed
        );
    }
    Ok(())
}

/// Cheapest model with at least three steps and four passes in five for this route.
/// (Routers plateau; a table of measured pass rates is as good as a learned one and honest.)
fn route(store: &Store, who: &str) -> Result<()> {
    let stats = route_stats(store)?;
    let mut candidates: Vec<(&(String, String), &RouteStat)> = stats
        .iter()
        .filter(|((w, _), s)| w == who && s.steps >= 3 && s.passed * 5 >= s.steps * 4)
        .collect();
    candidates.sort_by(|a, b| {
        let cost = |s: &RouteStat| {
            if s.priced {
                s.dollars / s.passed.max(1) as f64
            } else {
                f64::MAX
            }
        };
        cost(a.1)
            .partial_cmp(&cost(b.1))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    match candidates.first() {
        Some(((_, model), s)) => {
            let rate = 100 * s.passed / s.steps;
            let per = if s.priced {
                format!(", ${:.4} per passed step", s.dollars / s.passed as f64)
            } else {
                String::new()
            };
            println!("{who}: {model} ({rate}% of {} steps{per})", s.steps);
        }
        None => println!(
            "{who}: not enough data (need 3+ steps with 4 in 5 passing on one model); start with the small model and log who=, model=, in=, out=, result="
        ),
    }
    Ok(())
}

// ---------------------------------------------------------------- lessons

fn today() -> chrono::NaiveDate {
    chrono::Local::now().date_naive()
}

fn date_plus(days: i64) -> String {
    (today() + chrono::Duration::days(days))
        .format("%Y-%m-%d")
        .to_string()
}

fn lesson_in_force(l: &Lesson) -> bool {
    chrono::NaiveDate::parse_from_str(&l.valid_until, "%Y-%m-%d")
        .map(|d| d >= today())
        .unwrap_or(false)
}

/// Lessons from tool or web output stay quarantined until a person trusts them.
fn lesson_quarantined(l: &Lesson) -> bool {
    (l.source.starts_with("tool") || l.source.starts_with("web")) && !l.source.ends_with("trusted")
}

const LESSON_SOURCES: &[&str] = &["self", "reviewer", "user", "tool", "web"];

fn lesson_line(l: &Lesson, marks: bool) -> String {
    let mut flags = String::new();
    if marks {
        if lesson_quarantined(l) {
            flags.push_str(", quarantined");
        }
        if !lesson_in_force(l) {
            flags.push_str(", expired");
        }
    }
    format!(
        "{}. {} [{}, +{}/-{}{flags}]",
        l.id, l.text, l.scope, l.helpful, l.harmful
    )
}

fn lesson(store: &Store, cmd: LessonCmd) -> Result<()> {
    let mut lessons: Vec<Lesson> = store.load("lessons.json")?;
    match cmd {
        LessonCmd::Add {
            text,
            scope,
            source,
            run,
            days,
        } => {
            let source = source.trim().to_lowercase();
            if !LESSON_SOURCES.contains(&source.as_str()) {
                return Err(format!(
                    "--source must be one of {}",
                    LESSON_SOURCES.join(", ")
                ));
            }
            let scope = scope.trim().to_lowercase();
            if scope.is_empty() {
                return Err("--scope cannot be empty (use `global`)".into());
            }
            if !(1..=3650).contains(&days) {
                return Err("--days must be between 1 and 3650".into());
            }
            let id = next_id(lessons.iter().map(|l| l.id));
            let quarantined = matches!(source.as_str(), "tool" | "web");
            lessons.push(Lesson {
                id,
                text,
                scope,
                source,
                run,
                helpful: 0,
                harmful: 0,
                created: now(),
                valid_until: date_plus(days),
            });
            store.save("lessons.json", &lessons)?;
            println!(
                "lesson {id} added{}",
                if quarantined {
                    " (quarantined: from tool or web output; `sw lesson trust` after checking it)"
                } else {
                    ""
                }
            );
        }
        LessonCmd::List { all } => {
            for l in lessons
                .iter()
                .filter(|l| all || (lesson_in_force(l) && !lesson_quarantined(l)))
            {
                println!("{}", lesson_line(l, all));
            }
        }
        LessonCmd::Vote { id, direction } => {
            let l = find(&mut lessons, id, |l| l.id)?;
            match direction.as_str() {
                "up" => {
                    l.helpful += 1;
                    l.valid_until = date_plus(LESSON_RENEWAL_DAYS);
                }
                "down" => l.harmful += 1,
                other => return Err(format!("vote up or down, not '{other}'")),
            }
            let (helpful, harmful) = (l.helpful, l.harmful);
            store.save("lessons.json", &lessons)?;
            println!("lesson {id}: +{helpful}/-{harmful}");
        }
        LessonCmd::Trust { id } => {
            let l = find(&mut lessons, id, |l| l.id)?;
            if !l.source.ends_with("trusted") {
                l.source = format!("{}, trusted", l.source);
            }
            store.save("lessons.json", &lessons)?;
            println!("lesson {id} trusted");
        }
        LessonCmd::For { goal, all, limit } => {
            let goal = goal.to_lowercase();
            let mut hits: Vec<&Lesson> = lessons
                .iter()
                .filter(|l| l.scope == "global" || goal.contains(l.scope.as_str()))
                .filter(|l| all || (lesson_in_force(l) && !lesson_quarantined(l)))
                .collect();
            // Best first: net votes, then newest. Soft ranking, never a hard rule.
            hits.sort_by(|a, b| {
                let score = |l: &Lesson| l.helpful as i64 - l.harmful as i64;
                score(b)
                    .cmp(&score(a))
                    .then_with(|| b.created.cmp(&a.created))
            });
            for l in hits.iter().take(limit) {
                println!("{}", lesson_line(l, all));
            }
        }
    }
    Ok(())
}

fn status(store: &Store) -> Result<()> {
    let goals: Vec<Goal> = store.load("goals.json")?;
    let cards: Vec<Card> = store.load("inbox.json")?;
    let open = goals.iter().filter(|g| g.status == "open").count();
    let counts: Vec<String> = [Kind::Ask, Kind::Review, Kind::Notify, Kind::Idea]
        .iter()
        .map(|k| {
            format!(
                "{} {}",
                k.name(),
                cards
                    .iter()
                    .filter(|c| c.status == "open" && c.kind == *k)
                    .count()
            )
        })
        .collect();
    let answered = cards.iter().filter(|c| c.status == "answered").count();
    let profile = store.root.join("profile.md").exists();
    println!(
        "profile: {}",
        if profile {
            "yes"
        } else {
            "missing, run onboarding"
        }
    );
    let mut line = format!("goals: {open} open | inbox: {}", counts.join(", "));
    if answered > 0 {
        line.push_str(&format!(" | answered {answered} (apply, then close)"));
    }
    println!("{line}");
    if let Some(top) = goals
        .iter()
        .filter(|g| g.status == "open")
        .min_by_key(|g| (g.priority, g.id))
    {
        println!("top goal: {}. {}", top.id, top.text);
    }
    for c in cards
        .iter()
        .filter(|c| c.status != "closed" && matches!(c.kind, Kind::Ask | Kind::Review))
    {
        println!("needs you: {}. {}: {}", c.id, c.kind.name(), c.title);
    }
    if let Some(last) = store.runs()?.last() {
        let progress = Progress::of(last);
        println!(
            "last run: {} next: {}",
            file_name(last),
            progress.next_label()
        );
    }
    Ok(())
}

fn goal(store: &Store, cmd: GoalCmd) -> Result<()> {
    let mut goals: Vec<Goal> = store.load("goals.json")?;
    match cmd {
        GoalCmd::Add { text, priority } => {
            let id = next_id(goals.iter().map(|g| g.id));
            goals.push(Goal {
                id,
                text,
                priority,
                status: "open".into(),
                created: now(),
                closed: None,
                note: None,
            });
            store.save("goals.json", &goals)?;
            println!("goal {id} added");
        }
        GoalCmd::List { all } => {
            let mut shown: Vec<&Goal> =
                goals.iter().filter(|g| all || g.status == "open").collect();
            shown.sort_by_key(|g| (g.priority, g.id));
            for g in &shown {
                let tail = if g.status == "open" {
                    String::new()
                } else {
                    format!(" ({})", g.status)
                };
                println!("{}. [p{}] {}{tail}", g.id, g.priority, g.text);
            }
            if shown.is_empty() {
                println!("no open goals");
            }
        }
        GoalCmd::Done { id, note } => {
            let g = find(&mut goals, id, |g| g.id)?;
            g.status = "done".into();
            g.closed = Some(now());
            g.note = Some(note.unwrap_or_default());
            store.save("goals.json", &goals)?;
            println!("goal {id} done");
        }
    }
    Ok(())
}

fn run_cmd(store: &Store, cmd: RunCmd) -> Result<()> {
    match cmd {
        RunCmd::New { slug, goal } => {
            let base = format!(
                "{}-{}",
                chrono::Local::now().format("%Y%m%d-%H%M%S"),
                slugify(&slug)
            );
            let runs = store.root.join("runs");
            let mut dir = runs.join(&base);
            let mut n = 1;
            while dir.exists() {
                n += 1;
                dir = runs.join(format!("{base}-{n}"));
            }
            fs::create_dir_all(&dir)
                .map_err(|e| format!("cannot create {}: {e}", dir.display()))?;
            File::create(dir.join("log.jsonl")).map_err(|e| e.to_string())?;
            let cwd = std::env::current_dir()
                .ok()
                .and_then(|d| fs::canonicalize(d).ok())
                .map(|d| d.to_string_lossy().into_owned())
                .unwrap_or_default();
            {
                let goal = goal.map(|g| g.to_string()).unwrap_or_default();
                append_event(
                    &dir,
                    &[
                        ("event".into(), "start".into()),
                        ("cwd".into(), cwd),
                        ("goal".into(), goal),
                    ],
                )?;
            }
            println!("{}", dir.display());
        }
        RunCmd::Log { run, pairs } => {
            let mut parsed: Vec<(String, String)> = Vec::new();
            for pair in pairs {
                match pair.split_once('=') {
                    Some((k, v)) => {
                        if parsed.iter().any(|(seen, _)| seen == k) {
                            return Err(format!("duplicate key '{k}': each key once"));
                        }
                        parsed.push((k.to_string(), v.to_string()));
                    }
                    None => return Err(format!("expected key=value, got '{pair}'")),
                }
            }
            if let Some((k, _)) = parsed.iter().find(|(k, _)| SW_KEYS.contains(&k.as_str())) {
                return Err(format!(
                    "`{k}` is written by sw itself (receipts, snapshots, certified passes); it cannot be logged by hand"
                ));
            }
            let dir = store.resolve_run(&run)?;
            let value = |key: &str| {
                parsed
                    .iter()
                    .find(|(k, _)| k == key)
                    .map(|(_, v)| v.clone())
            };
            if let Some(step) = value("step") {
                let numeric = !step.is_empty()
                    && step.bytes().all(|b| b.is_ascii_digit())
                    && (step == "0" || !step.starts_with('0'));
                if !numeric {
                    return Err(format!("step must be a number as in plan.md, got '{step}'"));
                }
            }
            if let Some(result) = value("result") {
                if result != "pass" && result != "fail" {
                    return Err(format!("result must be pass or fail, got '{result}'"));
                }
            }
            let step_result = (value("step"), value("result"));
            if let (Some(step), Some(result)) = step_result {
                let plan = fs::read_to_string(dir.join("plan.md")).unwrap_or_default();
                let check = plan_step_check(&plan, &step);
                let is_command = check.as_deref().and_then(command_check).is_some();
                if result == "pass" && is_command {
                    return Err(format!(
                        "step {step} has a command check; a pass written by hand is not evidence. \
                         Run `sw run check {run} {step}`, then `sw run done {run} {step}`."
                    ));
                }
                if result == "pass" {
                    // The check the pass was logged against is the plan's, not the caller's.
                    parsed = with_evidence(parsed, &dir, &run, &step)?
                        .into_iter()
                        .filter(|(k, _)| k != "check")
                        .collect();
                    if let Some(check) = check {
                        parsed.push(("check".into(), check));
                    }
                }
                note_plan(&dir)?;
            }
            append_event(&dir, &parsed)?;
        }
        RunCmd::Status { run } => {
            let dir = store.resolve_run(&run)?;
            let p = Progress::of(&dir);
            println!(
                "{}: {}/{} steps passed",
                file_name(&dir),
                p.passed(),
                p.total()
            );
            let mut failing: Vec<(&String, &String)> =
                p.results.iter().filter(|(_, r)| *r != "pass").collect();
            failing.sort_by_key(|(s, _)| s.parse::<u64>().unwrap_or(0));
            for (step, result) in failing {
                println!("  step {step}: {result}");
            }
            for problem in evidence_problems(&dir)? {
                println!("  {problem}");
            }
            println!("next: {}", p.next_label());
        }
        RunCmd::List => {
            let runs = store.runs()?;
            for dir in runs.iter().rev().take(10).rev() {
                let p = Progress::of(dir);
                println!("{}  {}/{}", file_name(dir), p.passed(), p.total());
            }
        }
        RunCmd::Cost { run } => run_cost(store, &store.resolve_run(&run)?)?,
        RunCmd::Check { run, step } => run_check(&store.resolve_run(&run)?, &step)?,
        RunCmd::Done { run, step } => run_done(&store.resolve_run(&run)?, &step)?,
        RunCmd::Review { run, step } => run_review(&store.resolve_run(&run)?, &step)?,
        RunCmd::Freeze { run, paths } => run_freeze(&store.resolve_run(&run)?, &paths)?,
        RunCmd::Snapshot { run, step } => run_snapshot(&store.resolve_run(&run)?, &step)?,
        RunCmd::Rewind { run, step } => run_rewind(&store.resolve_run(&run)?, &step)?,
        RunCmd::Brief => run_brief(store)?,
        RunCmd::Stats => run_stats(store)?,
        RunCmd::Next { run } => {
            let dir = store.resolve_run(&run)?;
            let plan = fs::read_to_string(dir.join("plan.md")).unwrap_or_default();
            let runnable = runnable_steps(&plan, &step_results(&dir, &plan));
            if !runnable.is_empty() {
                println!("{}", runnable.join(" "));
            }
        }
    }
    Ok(())
}

/// Price per million tokens for one model, read from `prices.json` in the state folder:
/// `{"claude-haiku-4-5": {"in": 1.0, "out": 5.0}, ...}`. The user fills it from the vendor's
/// pricing page; sw never guesses a price.
#[derive(Deserialize)]
struct Price {
    #[serde(rename = "in")]
    input: f64,
    #[serde(rename = "out")]
    output: f64,
    /// Cache-read price per million; when absent, a tenth of the input price is assumed.
    #[serde(default)]
    read: Option<f64>,
}

/// Claude Code reports dated ids such as `claude-haiku-4-5-20251001`; prices are keyed by the
/// undated name, so strip one trailing `-YYYYMMDD`.
fn price_key(model: &str) -> &str {
    if let Some((head, tail)) = model.rsplit_once('-') {
        if tail.len() == 8 && tail.chars().all(|c| c.is_ascii_digit()) {
            return head;
        }
    }
    model
}

fn lookup<'a>(prices: &'a BTreeMap<String, Price>, model: &str) -> Option<&'a Price> {
    prices.get(model).or_else(|| prices.get(price_key(model)))
}

fn run_cost(store: &Store, run: &Path) -> Result<()> {
    let prices_path = store.root.join("prices.json");
    let prices: BTreeMap<String, Price> = match fs::read_to_string(&prices_path) {
        Ok(text) => serde_json::from_str(&text)
            .map_err(|e| format!("{} is not valid ({e})", prices_path.display()))?,
        Err(_) => BTreeMap::new(),
    };
    let text = fs::read_to_string(run.join("log.jsonl")).unwrap_or_default();
    // per model: (input tokens, output tokens)
    let mut used: BTreeMap<String, (f64, f64)> = BTreeMap::new();
    for line in text.lines() {
        let Ok(e) = serde_json::from_str::<serde_json::Map<String, serde_json::Value>>(line) else {
            continue;
        };
        let Some(model) = e.get("model").map(value_str) else {
            continue;
        };
        let num = |k: &str| {
            e.get(k)
                .map(value_str)
                .and_then(|v| v.parse::<f64>().ok())
                .unwrap_or(0.0)
        };
        let entry = used.entry(model).or_insert((0.0, 0.0));
        entry.0 += num("in");
        entry.1 += num("out");
    }
    if used.is_empty() {
        println!(
            "no token usage logged (add model=<name> in=<tokens> out=<tokens> to run log lines)"
        );
        return Ok(());
    }
    let mut total = 0.0;
    let mut unpriced = Vec::new();
    for (model, (i, o)) in &used {
        match lookup(&prices, model) {
            Some(p) => {
                let cost = (i * p.input + o * p.output) / 1_000_000.0;
                total += cost;
                println!("{model}: in {i:.0}, out {o:.0}, ${cost:.4}");
            }
            None => {
                unpriced.push(model.clone());
                println!("{model}: in {i:.0}, out {o:.0}, no price in prices.json");
            }
        }
    }
    println!("total: ${total:.4}");
    if !unpriced.is_empty() {
        return Err(format!(
            "no price for {}; add it to {}",
            unpriced.join(", "),
            prices_path.display()
        ));
    }
    Ok(())
}

fn inbox(store: &Store, cmd: InboxCmd) -> Result<()> {
    let mut cards: Vec<Card> = store.load("inbox.json")?;
    match cmd {
        InboxCmd::Add {
            kind,
            title,
            body,
            run,
        } => {
            // One name per run (`latest`, an id or a path all mean the same folder), so the
            // question budget cannot be dodged by spelling the run differently.
            let run = match run.filter(|r| !r.is_empty()) {
                Some(r) => store.resolve_run(&r).map(|d| file_name(&d)).unwrap_or(r),
                None => String::new(),
            };
            if matches!(kind, Kind::Ask) {
                // Question budget: more questions do not get more answers (Ask Less, Ask
                // Better; Ask Early, Ask Late, Ask Right). Three open per run, then act on
                // the reversible default and record the assumption.
                let open = cards
                    .iter()
                    .filter(|c| matches!(c.kind, Kind::Ask) && c.status == "open" && c.run == run)
                    .count();
                if open >= ASK_BUDGET {
                    return Err(format!(
                        "{open} questions are already open for this run (budget {ASK_BUDGET}); \
                         take the reversible default and note the assumption, or wait for an answer"
                    ));
                }
            }
            let id = next_id(cards.iter().map(|c| c.id));
            cards.push(Card {
                id,
                kind,
                title,
                body: body.unwrap_or_default(),
                run,
                status: "open".into(),
                created: now(),
                answer: None,
                answered: None,
                closed: None,
            });
            store.save("inbox.json", &cards)?;
            println!("inbox {id} ({}) added", kind.name());
        }
        InboxCmd::List { all } => {
            let mut shown: Vec<&Card> = cards
                .iter()
                .filter(|c| all || c.status == "open" || c.status == "answered")
                .collect();
            shown.sort_by_key(|c| (c.kind, c.id));
            for c in &shown {
                let tail = if c.status == "open" {
                    String::new()
                } else {
                    format!(" ({})", c.status)
                };
                println!("{}. {}: {}{tail}", c.id, c.kind.name(), c.title);
            }
            if shown.is_empty() {
                println!("inbox empty");
            }
        }
        InboxCmd::Show { id } => {
            let c = find(&mut cards, id, |c| c.id)?;
            println!("{}. {}: {} ({})", c.id, c.kind.name(), c.title, c.status);
            for (key, value) in [
                ("body", &c.body),
                ("answer", c.answer.as_ref().unwrap_or(&String::new())),
                ("run", &c.run),
            ] {
                if !value.is_empty() {
                    println!("{key}: {value}");
                }
            }
        }
        InboxCmd::Answer { id, answer } => {
            let c = find(&mut cards, id, |c| c.id)?;
            if c.status != "open" {
                return Err(format!(
                    "inbox {id} is {}, only open cards can be answered",
                    c.status
                ));
            }
            c.status = "answered".into();
            c.answer = Some(answer);
            c.answered = Some(now());
            store.save("inbox.json", &cards)?;
            println!("inbox {id} answered");
        }
        InboxCmd::Close { id, answer } => {
            let c = find(&mut cards, id, |c| c.id)?;
            c.status = "closed".into();
            c.closed = Some(now());
            if answer.is_some() {
                c.answer = answer;
            }
            store.save("inbox.json", &cards)?;
            println!("inbox {id} closed");
        }
    }
    Ok(())
}

fn note(store: &Store, cmd: NoteCmd) -> Result<()> {
    let mut notes: Vec<Note> = store.load("notes.json")?;
    match cmd {
        NoteCmd::Add { text, source, kind } => {
            let id = next_id(notes.iter().map(|n| n.id));
            notes.push(Note {
                id,
                text,
                kind,
                source,
                valid_from: now(),
                valid_to: None,
                retired_reason: None,
            });
            store.save("notes.json", &notes)?;
            println!("note {id} added");
        }
        NoteCmd::List { all } => {
            let shown: Vec<&Note> = notes
                .iter()
                .filter(|n| all || n.valid_to.is_none())
                .collect();
            for n in &shown {
                let tail = match &n.valid_to {
                    None => String::new(),
                    Some(_) => format!(
                        " (retired: {})",
                        n.retired_reason.clone().unwrap_or_default()
                    ),
                };
                let day: String = n.valid_from.chars().take(10).collect();
                println!(
                    "{}. [{}] {} (source: {}, {day}){tail}",
                    n.id,
                    n.kind.name(),
                    n.text,
                    n.source
                );
            }
            if shown.is_empty() {
                println!("no notes");
            }
        }
        NoteCmd::Retire { id, reason } => {
            let n = find(&mut notes, id, |n| n.id)?;
            n.valid_to = Some(now());
            n.retired_reason = Some(reason);
            store.save("notes.json", &notes)?;
            println!("note {id} retired");
        }
    }
    Ok(())
}

fn tool(store: &Store, cmd: ToolCmd) -> Result<()> {
    let mut tools: Vec<Tool> = store.load("tools.lock.json")?;
    match cmd {
        ToolCmd::Pin {
            name,
            path,
            source,
            force,
        } => {
            let path = fs::canonicalize(&path)
                .map_err(|_| format!("{} does not exist", path.display()))?;
            let digest = content_hash(&path)?;
            if let Some(old) = tools.iter().find(|t| t.name == name) {
                if old.sha256 != digest && !force {
                    return Err(format!("{name} changed since it was pinned; re-vet it, then pin again with --force"));
                }
            }
            tools.retain(|t| t.name != name);
            tools.push(Tool {
                name: name.clone(),
                path: path.display().to_string(),
                source: source.unwrap_or_default(),
                sha256: digest,
                pinned: now(),
            });
            store.save("tools.lock.json", &tools)?;
            println!("pinned {name}");
        }
        ToolCmd::Check => {
            let mut drift = 0;
            for t in &tools {
                let path = Path::new(&t.path);
                let state = if !path.exists() {
                    "MISSING"
                } else if content_hash(path)? != t.sha256 {
                    "CHANGED"
                } else {
                    "ok"
                };
                if state != "ok" {
                    drift += 1;
                }
                println!("{}: {state}", t.name);
            }
            if drift > 0 {
                return Err(format!(
                    "{drift} tool(s) changed since pinned: re-vet before use"
                ));
            }
        }
        ToolCmd::List => {
            for t in &tools {
                let shown = if t.source.is_empty() {
                    &t.path
                } else {
                    &t.source
                };
                println!(
                    "{}  {}  {shown}",
                    t.name,
                    &t.sha256[..12.min(t.sha256.len())]
                );
            }
            if tools.is_empty() {
                println!("no pinned tools");
            }
        }
    }
    Ok(())
}

fn main() -> ExitCode {
    match run(Cli::parse()) {
        Ok(()) => ExitCode::SUCCESS,
        Err(message) => {
            eprintln!("{message}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn step_checks_are_found_and_commands_recognised() {
        let plan = "# Goal\n1. a | who: self | check: $ cargo test | after: -\n2. b | check: reviewer reads it\n";
        assert_eq!(plan_step_check(plan, "1").as_deref(), Some("$ cargo test"));
        assert_eq!(command_check("$ cargo test"), Some("cargo test"));
        assert_eq!(
            plan_step_check(plan, "2").as_deref(),
            Some("reviewer reads it")
        );
        assert_eq!(command_check("reviewer reads it"), None);
        assert_eq!(command_check("$"), None);
        assert_eq!(command_check("$5 refund shown"), None);
        assert_eq!(plan_step_check(plan, "3"), None);
        let trailing = "1. a | check: $ true | who: self | after: 1\n";
        assert_eq!(plan_step_check(trailing, "1").as_deref(), Some("$ true"));
        let piped =
            "1. a | who: self | check: $ ls | wc -l | grep -q 2 | after: -\n2. b | check: $ true\n";
        assert_eq!(
            plan_step_check(piped, "1").as_deref(),
            Some("$ ls | wc -l | grep -q 2")
        );
        assert_eq!(plan_step_check(piped, "2").as_deref(), Some("$ true"));
    }

    #[test]
    fn steps_need_a_check() {
        let plan = "# Goal\n1. a | who: me | check: true\n2. b |check: x\n3. not a step\n10. c | check: y\nOutward: none";
        assert_eq!(plan_steps(plan), vec!["1", "2", "10"]);
    }

    #[test]
    fn slugs_are_safe_and_short() {
        assert_eq!(slugify("Build Thing!"), "build-thing");
        assert_eq!(slugify("***"), "run");
        assert_eq!(slugify(&"a".repeat(60)).len(), 40);
    }
}
