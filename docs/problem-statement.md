# Problem Statement

## Background

Questioned document examination is a core forensic discipline: examiners are asked to determine whether a certificate, signature, property deed, or FIR has been altered or forged. In India this workload has grown sharply — fake COVID vaccination certificates circulated across Telangana and UP in 2021, the Education Ministry recorded 3,000+ fake degree cases in 2022, and courts routinely receive forged property documents and altered FIRs. Each case requires the examiner to reason across several independent indicator types (typography, signatures, paper/substrate, ink, and — increasingly — digital metadata) and then translate that reasoning into a written opinion that can survive cross-examination.

## The Problem

Examiners currently record observations in free-form notes and produce opinions from memory and personal template files. There is no structured intake that forces consideration of every indicator category, no consistent way to turn a set of observations into a confidence level, and no direct link from a finding to the examination standard that justifies it. This makes throughput slow, makes opinions harder to defend under cross-examination (because the reasoning trail isn't explicit), and makes it hard for a junior examiner's work to be reviewed quickly by a senior one.

## Who is Affected

Forensic document examiners at state Forensic Science Laboratories (FSLs) and NFSU-affiliated labs who are handling a backlog of suspected-forgery cases — certificates, degrees, property documents, and FIRs — under time pressure, plus the investigating officers and courts waiting on their opinions.

## Why It Matters

Backlogged FSLs already delay case resolution by weeks; a case-management layer that structures the intake and drafts the first pass of the report can materially cut per-case turnaround time. Just as importantly, a documented, standards-linked reasoning trail makes the resulting opinion more defensible in court — reducing the risk of an opinion being challenged or thrown out for lack of a clear methodology.

## Why Existing Solutions Fall Short

Existing tools are either general-purpose document editors (no forensic structure at all) or specialized imaging hardware/software focused on the physical examination itself (microscopy, ESDA, VSC) — none of them provide a reasoning and reporting layer that sits on top of an examiner's observations to classify, score, and draft. DocuVerity is deliberately scoped to that missing layer: it does not replace physical/instrumental examination, it structures and accelerates the human reasoning and report-writing step that follows it.
