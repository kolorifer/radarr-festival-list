# Movie notifications: a practical guide

This guide follows a movie release from an autobrr announcement to Radarr, Telegram and, when you choose, a download. It describes the setup checked on **27 October 2026**. Your own Radarr profiles and autobrr filters determine many outcomes, so individual messages can differ. Features marked **shadow pilot** are being tested; they do not make production decisions.

**31 October code-only addition — inactive AI investigator:** a new standalone
module can review a captured failed-identification event using retained evidence
and prior choices for that exact occurrence. Its offline proof uses synthetic
data and simulated model replies; it has not identified a real new movie.
Real model use is blocked until the client's complete tool and context boundary
is independently established. It is not connected to Telegram or a daily
schedule. Its private daily view shows evidence, prior decisions, uncertainty
and next actions without marking anything delivered or acknowledged. A skipped
or completed occurrence stays scoped to that occurrence; an earlier shadow
success remains dated knowledge, and a known film may still need source, runtime
or edition verification. This code does not change original notifications,
identity choices or the separate download-confirmation step. See the
[inactive investigator documentation](AI-MOVIE-INVESTIGATOR.md). The corrective
pass rechecks evidence and earlier choices as time passes; an expired or changed
choice cannot silently authorize a later result. Real-client isolation still
needs independent proof, and the investigator remains disabled.
The latest code correction removes an unsupported client setting. Read-only
client checks accept the remaining settings; that does not prove that skills,
tools or inherited instructions are isolated and does not enable real use.

## The people and programs involved

- **Tracker:** announces a torrent release, such as a particular Blu-ray version of a film.
- **autobrr:** watches announcements and applies your filters. Only a selected release is sent onward by the relevant action.
- **Radarr:** maintains your movie library and decides whether an incoming release is wanted, meets its rules and is an improvement over an existing file.
- **movie-intel:** receives event information, checks movie identity, adds context and sends Telegram messages. It also hosts the private confirmation pages.
- **Identity collector and research worker:** keep track of selected releases and investigate unresolved identities in the background. They do not download films.
- **qBittorrent:** downloads a torrent when Radarr or an explicitly confirmed alternative-grab action submits it.

A *movie* and a *release* are different things. A movie is the work in Radarr; a release is one particular torrent for it. Two releases can be the same film with different quality, languages or cuts.

## From announcement to Radarr

1. A tracker announces a release. autobrr checks it against the filters you configured. A release that does not pass the relevant filter is not sent by that filter's action, and the identity collector is intended to record selected releases rather than every incoming announcement.
2. For a selected release, autobrr sends the release to Radarr. An accepted release can go to Radarr's configured download client automatically. The separate **Add to Radarr & grab** and **Grab Anyway** buttons described below require your explicit action.
3. Radarr parses the release name, tries to match a movie in its library and applies its own settings. The result depends on the movie's monitoring state, quality profile, language and custom formats, existing file, download client and other configured rules. The notification shows the reason Radarr supplied; it is not a guarantee that all possible problems have been listed.
4. The event sent to movie-intel is used to produce the applicable Telegram message and, where supported, an action. Not every event has a button. An ordinary message is informative; it does not itself approve a download.

Radarr settings can change independently of this guide. For example, if a film is already monitored and the release meets its rules, Radarr may accept it; if it has an equal or better existing file, Radarr may reject it; if it cannot match the release to a library entry, it may report **Unknown Movie**. Other causes include a profile, language or parsing rejection. Accepted does not mean the download or import has completed.

## Telegram topics and message types

The configured topics are **458** for general messages, **1466** for Add to Radarr & Grab actions, and **1468** for Grab Anyway actions. Unknown Movie notifications are routed to 1466 even when identity is not yet verified and no button is available. Alternative-release notifications route to 1468. General alerts and identification digests use 458; routing depends on the current configuration. Earlier messages are not automatically moved when settings change.

| Message | What it means | What you can do |
| --- | --- | --- |
| **Radarr — Unknown Movie** | Radarr could not match the release to an existing movie in its library. This does not necessarily mean the film is absent from IMDb or TMDb. | If identity and the original release are verified, an add-and-grab button may appear. If identity conflicts, a review button may be available. |
| **Radarr — Release Rejected** | Radarr recognised a movie but rejected this release, often because an existing file meets its quality or custom-format rules. The message includes Radarr's reason. | Eligible existing-file rejections may offer Grab Anyway. Other reasons can remain informational. |
| **Radarr — Rejected** | Another rejection or an event that is not eligible for the routine quality category. | Read the displayed reason; a button is not guaranteed. |
| **Release Accepted / Release Error** | An accepted event or error is reported when the configured event reaches movie-intel. An edition annotation may be included for supported events. | Check Radarr and the downloader for the actual outcome. |
| **Movie identification update** | A digest of new or changed investigation cases. It can report pending research, a conflict or a proposed identity. | Review the evidence; a research proposal is not an approval. |
| **Connection or update alert** | Operational notification from the configured notifier. | Check the service named in the alert. |

Messages can include the movie title, year, release name, Radarr's reason, links, poster, ratings, genres, runtime and Movie List recognition when those facts are available. A Movie List qualification or “potential false negative” is information about the project's catalog; it is not a command to download. Missing information is not filled in with a guess.

## How movie identity is checked in production

An incoming name alone is not always reliable: it may have a typo, an alternate title, an incorrect year or a tracker link for a different film. movie-intel combines the information actually available, including release and indexer identifiers, the local catalog, TMDb and, when configured, the exact TorrentLeech listing.

The process is deliberately cautious:

1. It checks that the event describes a movie and that its identifiers are well formed. Contradictory identifiers or a movie-versus-series conflict need review.
2. It checks the exact tracker listing when that lookup is available and appropriate. The listing must belong to the release being examined. Its IMDb association is useful evidence, but a link alone is not a verified TMDb movie.
3. It checks the IMDb/TMDb mapping and supporting title and year information. A verified movie may be outside the project's local Movie List; that does not by itself make its identity invalid.
4. The production rules support a single-letter typo in words of at least six letters when the checked tracker IMDb, the TMDb mapping and year agree. For example, Carrue can match Carrie when those checks succeed; a title alone is not enough. A five-letter word may also contain one typo when another unchanged alphabetic word of at least six letters supplies context. Standalone Alien/Aliens and The Thing/The Think remain outside this rule. Stronger disagreement, ambiguous mappings, missing records or an actual conflicting ID stay blocked or require review. Another generic rule can identify a movie when a documented title or alias, NFO runtime and audio language, a unique IMDb–TMDb mapping and a documented release year all agree. Unsupported NFO layouts or missing evidence still need review. These checks do not turn a reviewed conflict into a permanent exception.
For an already verified movie with the same IMDb ID on the exact tracker listing, the runtime check allows a difference of up to 5% of the catalog runtime, capped at five minutes. The existing one-minute rounding allowance remains. Larger differences still block identification and are checked again before an acquisition; a 12-minute short cannot pass as a 93-minute feature. This does not establish which cut or edition is present. The parser reads one General-section runtime, including MediaInfo `Length: file size for duration`, with seconds when provided; video/audio track durations are excluded.

5. Tracker descriptions, NFO text and image references may be retained as evidence for investigations. An **NFO** is a text file supplied with a release, often listing the filename, runtime and audio tracks. Screenshot references are collected for a person to inspect; the system does not automatically understand their images.

A temporary service failure or rate limit means identity verification is unavailable at that moment. The message can say that approval is unavailable. An IMDb-only association means the system has not confirmed the corresponding TMDb movie. A conflict means the available facts disagree or cannot safely be reconciled. In each case, absence of a button is intentional until its requirements are met.

The system can recheck some temporary failures within bounded request and retry limits. For an eligible exact-tracker conflict it can also recheck after about 15 minutes, subject to the existing budget and service availability, in case the tracker corrected its metadata. If the conflict remains, review is still required. Successful or exhausted retries can update the original Telegram message where supported; old messages are not guaranteed to be retroactively repaired. A retry can be delayed by a provider outage, a budget, an expired action or missing source data.

## What the buttons do

### Add to Radarr & grab this release

This button is for a supported **Unknown Movie** event with a verified identity and a usable reference to the exact announced release. It opens a confirmation page; opening it does not start a download.

On the page, review the movie and release, choose from the available Radarr root folders and quality profiles, and confirm. The service rechecks the action and movie identity. It adds the movie if necessary with automatic search disabled, then sends the **original release reference** to Radarr for that specific release. Radarr still applies its own rules and download-client configuration. A successful submission is not proof that the download finished or that the file was imported. Existing movie state, an expired link, a changed source, a missing profile or an unavailable service can stop the action.

### Grab Anyway

This is for certain supported rejections where Radarr has a matching monitored movie with an existing file and rejected the new release because of an existing-file quality or equal/higher custom-format score. It is not a general override for every Radarr rejection. The film identity, existing movie and file, supported source and original release reference must all be verified. Mixed or unsupported rejection reasons can prevent the button.

The page compares the available existing and new-release details. Unknown details remain unknown. You must explicitly confirm **this exact release and the possibility that Radarr replaces your existing file**. After rechecking the movie and file, a restricted helper obtains that exact torrent and submits it to qBittorrent's configured Radarr category. Radarr may then import it and replace the old file. The release might be worse for your purposes despite being different. The button does not change your Radarr profiles or initiate a broad search.

A queued torrent is not proof of a completed download or replacement. If submission is uncertain, do not repeatedly click or assume it failed: check qBittorrent and Radarr first. The system keeps receipts and does not automatically retry uncertain submissions. Unsupported torrent types or a source that no longer works can also stop the action.

### Review evidence & choose movie

For a supported identity conflict, this opens a private review page containing available evidence and candidate choices. Check titles, years, IDs and the evidence carefully; choose only when you are satisfied. A choice concerns **that occurrence**. It does not create a permanent exception or teach the system to accept the same torrent next time without fresh review. Choosing an identity is separate from confirming any download, and the action is revalidated before acquisition.

Not every unresolved case can produce a review page. Missing or conflicting data, unavailable services, expired actions or an unsupported source may leave only an informational message. A previously reviewed occurrence can be marked reviewed for workflow purposes while a later occurrence still requires a fresh choice.

### Links, expiry and repeated clicks

Action links are private capabilities: do not share them. They expire, and an action may become unavailable if the release, source or Radarr movie/file changed. The service tracks attempts to avoid accidental duplicate submissions. If a result is uncertain, inspect the relevant service instead of forcing a retry. A notification's button is not a promise that a later submission will still be safe or possible.

## Background investigation and the review list

The collector records selected release observations and associates them with identity outcomes where it can do so safely. It deduplicates repeated observations, retains history and distinguishes verified, routine, unresolved, conflicting and unsuitable cases. An *investigation queue* is simply the private list of cases waiting for evidence or review; it is not a download queue. Correlation can fail if the original reference or reliable identifying details are missing.

The research worker periodically investigates eligible cases with limited, recorded provider requests. It can gather tracker descriptions, NFOs and screenshot references and compare candidate movie records. It retains uncertainty and produces proposals for review. Temporary failures, missing tracker IDs, mismatched headings, exhausted budgets and the daily schedule can delay results. The Telegram digest reports changed cases; it does not make corrections or downloads. Statuses are snapshots and can become stale, so check the latest evidence when reviewing a case.

When reviewing unresolved movies, review the full current unresolved set together, including evidence, proposed matches and remaining gaps. A case marked reviewed for one occurrence is not a permanent movie-specific rule.

## The evidence-scoring pilot: shadow only

A separate pilot tests whether multiple attributes can support a movie proposal. It may compare name similarity (including small typos), year, runtime, original-language audio and verified source identifiers. The trial weights are up to **30, 20, 15, 10 and 25 points** respectively; disagreements can reduce points. A small runtime difference reduces runtime points gradually. A score is not a percentage probability.

The pilot compares plausible rivals and requires safeguards in addition to a score. Missing evidence, incomplete candidate searches, conflicting IDs or uncertain source binding can still require review. Commentary tracks do not establish the film's original language. Multiple film-audio languages are considered without awarding the language weight repeatedly.

It can look for evidence about collection packaging and cut/edition names using bounded public sources and a cache. An edition-runtime explanation is an additional proposal, not proof of the file's contents. A bounded NFO original-title search can be used when ordinary title searches find no candidates and the exact listing and NFO filename are safely bound. Actual tracker-heading mismatches remain blocked.

This pilot is **not the production identification algorithm** and does not approve movies, send downloads or replace the live rules. Its second bounded run is scheduled through **3 November 2026, 21:18 Warsaw**, with at most 10 requests per run and 40 per UTC day; other workers have their own budgets. It reuses dated prior results and checkpoints partial work. A pilot result labelled “would identify” is a proposal for later evaluation, not an approved identity. Its deadline and current status should be checked before relying on it.

## Common questions

**Why is there no button?** The event may not support an action, the identity or exact source may be unverified, the rejection may not qualify, the movie/file may have changed, the link may have expired, or a service/configuration may be unavailable. A checked IMDb link by itself is not enough to establish every required fact.

**Why does Radarr say Unknown Movie for a real film?** Radarr is saying it cannot match this release to an existing library movie using the information it received. The film can still exist in external catalogs.

**Will a typo always be corrected automatically?** No. Minor typos can be handled when the required verified identity and year evidence agree. A wrong tracker link or another conflict must not be silently overridden.

**Will confirming a movie automatically download it?** Choosing a movie in an identity review and confirming a download are separate actions. Conversely, Radarr can automatically accept and download a release for an already configured movie under your normal Radarr rules.

**Can an old file be replaced?** Yes. In particular, the Grab Anyway confirmation explicitly allows Radarr to replace the existing file if its normal import process does so. A queued download alone does not prove replacement.

**Does research inspect screenshots for me?** It collects available image references for human review; it does not automatically interpret them.

**What if a retry succeeds after the first message?** Supported retries can update the original Telegram message with the new status and applicable button. If an action has expired or the message cannot be edited, check the latest status rather than assuming the old message remains actionable.

## Keeping this guide current

Update this file when notification routing, identification rules, action behavior, safety checks or pilot status change. State the verification date and distinguish deployed behavior from experiments. Do not include private tracker links, credentials, personal tokens or private service URLs. Engineering details and deployment records are in [project state](PROJECT_STATE.md), [decisions](DECISIONS.md), and [deployment instructions](../deploy/README.md).

## Offline investigation reporting support — code awaiting review

A separate coordinator reader can preserve the original investigation snapshot
and research report for private review, with distinct diagnostics for unreadable,
invalid, stale or incompatible evidence. It has been checked with synthetic files
only. The corrected reader rejects checkout/source destination aliases before
creating output, including double-leading-slash spellings and filesystem identity
aliases. Ancestor inspection failures close internally opened handles. It does
not activate a daily reporting agent or change notification routing,
identity choices, confirmation buttons or download safeguards. The
[coordinator guide](../automation/COORDINATOR.md#confined-movie-export-readerstager-issue-115-offline-code)
explains the contract and separate authorization needed for any real source use.

## Coordinator reporting cycles (offline implementation, 30 October 2026)

A separate local reporting tool can read supplied investigation exports and
engineering evidence, retain immutable reports, verify separately supplied
publication and system-recipient receipts, and archive completed reports with
their original evidence. Synthetic tests exercise the lifecycle; no recurring
reporting service or real report delivery has been activated by this work.
Missing or stale movie evidence remains visible, and production quality/release
coverage is still unavailable. A receipt for ingestion by a named system does
not mean a human read the report, accepted engineering work or approved a movie
or download. Existing Telegram routing, digest ownership, identity rules and
confirmation safeguards continue unchanged. See the
[cycle owner runbook](../automation/COORDINATOR_CYCLES.md).

The offline cycle correction checks source/state separation before any state
writes and binds the exact retained evidence into each report. Unsafe paths or
changed/missing evidence stop the cycle without silently approving publication
or deleting its recoverable record. Older cycle-format records are preserved
and require owner investigation; they are not automatically converted. These
checks were tested with synthetic data only and do not activate live reporting
or change movie notification or download approval behavior.
