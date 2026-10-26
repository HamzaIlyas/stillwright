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
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::ExitCode;

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
}

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

impl Store {
    fn open() -> Result<Self> {
        let root = match std::env::var_os("STILLWRIGHT_HOME").filter(|v| !v.is_empty()) {
            Some(v) => PathBuf::from(v),
            None => home_dir()?.join(".stillwright"),
        };
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

fn step_results(run: &Path) -> BTreeMap<String, String> {
    let mut results = BTreeMap::new();
    let text = fs::read_to_string(run.join("log.jsonl")).unwrap_or_default();
    for (n, line) in text.lines().enumerate() {
        if line.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<serde_json::Map<String, serde_json::Value>>(line) {
            Ok(event) => {
                if let (Some(step), Some(result)) = (event.get("step"), event.get("result")) {
                    results.insert(value_str(step), value_str(result));
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
        let steps = fs::read_to_string(run.join("plan.md"))
            .map(|p| plan_steps(&p))
            .unwrap_or_default();
        let results = step_results(run);
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
    event.insert("ts".into(), now().into());
    for (k, v) in pairs {
        event.insert(k.clone(), v.clone().into());
    }
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(run.join("log.jsonl"))
        .map_err(|e| format!("cannot open run log: {e}"))?;
    writeln!(file, "{}", serde_json::Value::Object(event)).map_err(|e| e.to_string())
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

fn run(cli: Cli) -> Result<()> {
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
    }
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
            if let Some(goal) = goal {
                append_event(
                    &dir,
                    &[
                        ("event".into(), "start".into()),
                        ("goal".into(), goal.to_string()),
                    ],
                )?;
            }
            println!("{}", dir.display());
        }
        RunCmd::Log { run, pairs } => {
            let mut parsed = Vec::new();
            for pair in pairs {
                match pair.split_once('=') {
                    Some((k, v)) => parsed.push((k.to_string(), v.to_string())),
                    None => return Err(format!("expected key=value, got '{pair}'")),
                }
            }
            append_event(&store.resolve_run(&run)?, &parsed)?;
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
            let id = next_id(cards.iter().map(|c| c.id));
            cards.push(Card {
                id,
                kind,
                title,
                body: body.unwrap_or_default(),
                run: run.unwrap_or_default(),
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
