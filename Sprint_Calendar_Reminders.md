# AAAI 2027 Sprint — Calendar Reminders

**Period:** 2026-06-30 → 2026-07-28
**Project:** PrecedentGuard
**Purpose:** Cross-device backup of CronCreate-scheduled check-ins.

---

## How to Use This File

This is a manual calendar list. Import these 9 events into your phone/laptop calendar app as a backup to the Claude Code CronCreate jobs.

### Quick Import (recommended)

Copy the `.ics` block at the end into a file `precedentguard_sprint.ics` and double-click it. Most calendar apps (Google Calendar, Outlook, Apple Calendar) auto-import.

### Manual Import (fallback)

Create each event by hand using the table below.

---

## 9 Check-In Events

| # | Date | Time | Type | Title | Action Required |
|---|------|------|------|-------|-----------------|
| 1 | **Tue Jul 1, 2026** | 18:07 | Day 1 EOD | PG Sprint — Day 1 EOD review | Check proof skeleton progress; resolve TODO/VERIFY |
| 2 | **Fri Jul 4, 2026** | 17:53 | 🚨 Gate α | PG Sprint — GATE α (Theory Freeze) | BLOCKING: theorems + min impl + Related Work |
| 3 | **Tue Jul 8, 2026** | 18:11 | Pulse | PG Sprint — Week 2 mid pulse | Light: baseline impl progress |
| 4 | **Fri Jul 11, 2026** | 17:48 | 🚨 Gate β | PG Sprint — GATE β (Certificate) | BLOCKING: certificate validity on dev set |
| 5 | **Tue Jul 15, 2026** | 18:13 | Pulse | PG Sprint — Week 3 mid pulse | Light: 3 benchmark suite progress |
| 6 | **Fri Jul 18, 2026** | 17:51 | 🚨 Gate γ | PG Sprint — GATE γ (Freeze) | BLOCKING: tables/figures frozen |
| 7 | **Mon Jul 21, 2026** | 10:23 | 🛑 Abstract | PG Sprint — ABSTRACT due 17:00 | SUBMIT BY 16:00; AAAI abstract deadline |
| 8 | **Sun Jul 27, 2026** | 18:09 | Final review | PG Sprint — Final review | Red-team integration; final audit |
| 9 | **Mon Jul 28, 2026** | 09:17 | 🛑 Paper | PG Sprint — PAPER due 17:00 | SUBMIT BY 12:00; AAAI paper deadline |

---

## Stop-Loss Decision Rules (memorize)

| Gate | If FAIL → |
|------|----------|
| Gate α | STOP sprint → NeurIPS 2027 (May 2027 deadline) — lose 5 days |
| Gate β | STOP sprint → NeurIPS 2027 — lose 12 days |
| Gate γ | Cut content → ICLR 2028 (Sep 2026 deadline) — lose 19 days, still feasible |

**Iron rule:** No soldiering through a failed gate.

---

## .ics Calendar Block (copy/paste to file `precedentguard_sprint.ics`)

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PrecedentGuard//AAAI2027 Sprint//EN
CALSCALE:GREGORIAN

BEGIN:VEVENT
UID:pg-sprint-001@local
DTSTAMP:20260630T120000Z
DTSTART:20260701T180700
DTEND:20260701T182700
SUMMARY:PG Sprint — Day 1 EOD review
DESCRIPTION:Check proof skeleton compile + 4 results elaboration progress. Resolve TODO/VERIFY markers.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-002@local
DTSTAMP:20260630T120000Z
DTSTART:20260704T175300
DTEND:20260704T181300
SUMMARY:PG Sprint — 🚨 GATE α (Theory Freeze)
DESCRIPTION:BLOCKING gate. Criteria: all 4 proofs verified + min impl runs + Related Work updated. FAIL → STOP → NeurIPS 2027.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-003@local
DTSTAMP:20260630T120000Z
DTSTART:20260708T181100
DTEND:20260708T183100
SUMMARY:PG Sprint — Week 2 mid pulse
DESCRIPTION:Light check-in. Baseline implementation progress (target: 5+/8 baselines running).
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-004@local
DTSTAMP:20260630T120000Z
DTSTART:20260711T174800
DTEND:20260711T180800
SUMMARY:PG Sprint — 🚨 GATE β (Certificate Validity)
DESCRIPTION:BLOCKING gate. Criteria: certificate valid on dev set (≥4/5 seeds), all 8 baselines complete, 4 trust variants compared. FAIL → STOP → NeurIPS 2027.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-005@local
DTSTAMP:20260630T120000Z
DTSTART:20260715T181300
DTEND:20260715T183300
SUMMARY:PG Sprint — Week 3 mid pulse
DESCRIPTION:Light check-in. 3 benchmark suite progress. Triage decision if 2+ suites incomplete.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-006@local
DTSTAMP:20260630T120000Z
DTSTART:20260718T175100
DTEND:20260718T181100
SUMMARY:PG Sprint — 🚨 GATE γ (Tables/Figures Freeze)
DESCRIPTION:BLOCKING gate. Criteria: 3 suites complete, adaptive attack done, all 4 figures + 3 tables frozen, 7-page narrative drafted. FAIL → cut content + ICLR 2028.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-007@local
DTSTAMP:20260630T120000Z
DTSTART:20260721T102300
DTEND:20260721T104300
SUMMARY:PG Sprint — 🛑 AAAI Abstract due 17:00
DESCRIPTION:Submit by 16:00 (NOT 16:59). Verify all numerical claims against logged experiments.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-008@local
DTSTAMP:20260630T120000Z
DTSTART:20260727T180900
DTEND:20260727T182900
SUMMARY:PG Sprint — Final review (eve of submission)
DESCRIPTION:Red-team feedback integrated, DOI/arXiv verified, LaTeX compiles cleanly, repro checklist done. Lock tomorrow submission target = noon.
END:VEVENT

BEGIN:VEVENT
UID:pg-sprint-009@local
DTSTAMP:20260630T120000Z
DTSTART:20260728T091700
DTEND:20260728T093700
SUMMARY:PG Sprint — 🛑 AAAI Paper due 17:00
DESCRIPTION:Submit by 12:00 noon (NOT 16:59). AAAI portal historically congests in final hour. Final PDF + supplementary packaged.
END:VEVENT

END:VCALENDAR
```

---

## What to do at each event

### Day 1 EOD (Jul 1) — Day 1 review

Open `precedentguard_theorems_v0.2_skeleton.tex`. Confirm:
- [ ] File compiles
- [ ] Read through 4 results
- [ ] All TODOs and VERIFYs noted

### Gate α (Jul 4) — BLOCKING

Open `Sprint_Dashboard_4Week_AAAI27.md` § Gate α. If all 3 criteria PASS, post a 1-sentence confirmation. If any FAILS, follow stop-loss protocol immediately.

### Week 2 Pulse (Jul 8) — Light

Quick status check: baselines running? Suite construction on schedule?

### Gate β (Jul 11) — BLOCKING

Certificate validity is the load-bearing test. If empirical exceeds predicted bound on dev set, the theory needs adjustment — and there is no time. Stop-loss to NeurIPS 2027.

### Week 3 Pulse (Jul 15) — Light

If 2+ suites incomplete, triage immediately (cut Suite C).

### Gate γ (Jul 18) — BLOCKING

Tables and figures must be frozen by EOD. Any "almost done" item is NOT done.

### Abstract Day (Jul 21) — SUBMIT BY 16:00

Hard wall. Do not wait. Submit at 16:00 sharp.

### Final Review (Jul 27)

The night-before checklist. Integrate all red-team feedback. Verify every citation.

### Submission Day (Jul 28) — SUBMIT BY 12:00

Hard wall. Submit at noon. AAAI portal congests in final hour every year.

---

## Failure recovery

If you miss a Claude Code CronCreate ping (because Claude is closed), the calendar entry in your phone will still fire. That's the point of dual backup.

If you miss BOTH backups, the next time you open Claude Code, the missed durable jobs will be surfaced for catch-up. But by then time has been lost — set the calendar **right now**, before closing this file.

---

**Calendar file version:** v1.0
**Generated:** 2026-06-30 evening
**Coverage:** 9 check-ins over 28 days
**Average cadence:** every 3.1 days
