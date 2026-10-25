# Remembered movie identity with explicit confirmation

The user requested storing successful identifications for later torrents of the
same movie. On 2026-10-25 they selected option 2: show the remembered match for
identity confirmation before enabling Grab Anyway. Download confirmation remains
separate. This is the accepted extension to D005; automatic title/year approval
was not selected.

Acceptance:
- Persist successful exact-ID/context validation responses, with expiry and bounds.
- Remember only independently verified movie matches by exact source/title/year;
  no fuzzy names, alternate years, TV fields, or remembered owner-choice feedback.
- On temporary metadata failure, offer a unique remembered identity as a proposal.
  New explicit ID conflicts, contradictory evidence, mixed rejections and expired
  or ambiguous memory must not enable acquisition.
- Identity confirmation applies only to this immutable release occurrence. It
  must not download or create a permanent correction. A separate confirmation
  prepares and approves the original release through existing safeguards.
- Preserve each torrent's original source, link, rejection, quality and cut.
- Revalidate the live choice and cached identity before acquisition, including
  the restricted Grab Anyway helper; replay cannot recreate a completed child.
- Seed recent retained independent verified outcomes with their original times;
  never import unverified suggestions, owner decisions or acquisition approvals.
- Validate and deploy atop the running revision, preserving existing approvals,
  receipts, retry budgets, Telegram routing and unrelated services.
- No deliberate live notifications, downloads, imports or Radarr changes.

Implementation choices: TorrentLeech only (the supported Grab Anyway source);
exact Unicode NFC/case-folded/whitespace-normalized titles and exact integer year;
seven-day cache lifetime, 1,024 combined records, 32 KiB per record; private 700
parent and 600 SQLite file. Cache unavailability falls back to ordinary lookup or
blocks a remembered choice, never bypasses confirmation.
