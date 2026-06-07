---
name: recommend_hpc_io_followup
title: Recommend HPC I/O Follow-Up
description: Recommend concrete follow-up checks for an HPC I/O regression.
---

Recommend follow-up actions that match the observed regression. Examples:
inspect collective buffering settings, compare MPI-IO hints, check file layout
and striping, inspect metadata-heavy file creation patterns, and rerun a small
controlled trace with the same rank count and byte volume.

Keep recommendations tied to the evidence. Avoid generic performance advice
that does not follow from the parsed traces.
