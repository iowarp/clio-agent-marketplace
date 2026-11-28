# Ingesting HDF5 into clio-core (CTE/CAE)

## Purpose

Covers **whether** routing an HDF5 file through clio-core's blob store
(ingest via the CAE assimilator = `context_bundle`, read back via the CTE data
plane) pays off compared with reading it natively with h5py — and **how** ingest
avoids the slow paths. Guidance is grounded in benchmarking on the
dev-container build (functional/relative comparison, not absolute GB/s); the figures below come from that build, so re-measure on yours.

## TL;DR findings

- **Native h5py reads are faster.** Bundling into clio-core is *not* a
  read-latency optimization — across every fixture tested, clio-core read
  latency is higher than native h5py (2–8× warm; never lower than even a *cold*
  native read). clio-core's value is its *other* properties (cross-node shared
  residency, multi-tier placement), not faster reads for a single client.
- **Concurrent readers on ONE node do not change this.** Benchmarked N=1..8
  readers of the same dataset: clio-core lost to native h5py at every N and was
  slower than even a cold native read, with aggregate throughput plateauing
  (~1400 MB/s, single-daemon serialization) and ~2× the memory. On a single node
  the OS page cache already gives concurrent readers a shared cached copy for
  free. clio-core's sharing benefit is for **cross-node** sharing and
  **larger-than-RAM** working sets — neither of which native h5py + a local page
  cache can serve, and neither tested here. Single-node concurrency is not a
  clio-core win.
- **Ingest cost is per object.** The cost is per-*object*, not
  per-byte. Many small datasets are catastrophic; few large datasets are fine.

## Practice 1 — Consolidate small datasets before ingest (biggest lever)

Ingest + retrieve cost scales **linearly with dataset (object) count**, at a
near-constant **~11–20 ms per dataset** for a full read — versus ~0.1 ms/dataset
for native h5py. That is a **~100–200× per-object penalty**, measured across
10 → 8,533 datasets:

| datasets | native read | clio-core read | penalty |
|---:|---:|---:|---:|
| 10 | 1.3 ms | 115 ms | ~90× |
| 100 | 11 ms | 1.1 s | ~100× |
| 1,000 | 112 ms | 12.4 s | ~110× |
| 8,533 | 0.9 s | 173 s | ~196× |

**Effect:** consolidating a file with thousands of small datasets into fewer,
larger datasets before bundling removes most of that cost (concatenate along a new axis, or pack into one
table). A file that is one big dataset bundles in tens of ms; the same bytes
spread over thousands of datasets take minutes. Without consolidation, native h5py is
faster.

## Practice 2 — Bundling does not make reads faster (it doesn't amortize)

The intuition "pay ingest once, then cheap reads forever" does **not** hold here.
Break-even N (reads before ingest pays off) was **"never" at every scale** —
clio-core's warm read is slower than a *cold* native read even for large
contiguous data:

| dataset size | native cold | native warm | clio-core warm | break-even |
|---:|---:|---:|---:|---:|
| 256 MB | 293 ms | 61 ms | 396 ms | never |
| 1 GB | 1.1 s | 225 ms | 1.55 s | never |
| 2 GB | 2.1 s | 398 ms | 3.2 s | never |

The cost is **per-chunk** (CTE re-chunks at 1.5 MB → a 2 GB dataset is ~1,400
blobs, each a round-trip). **Effect:** sharing/tiering needs justify bundling;
read speed does not. The only situation where bundling can win is when the
*native* read is itself unusually expensive (e.g. heavily strided/random access)
**and** the file is re-read many times — a quick A/B shows whether it does.

## Practice 3 — Selective retrieve for subsets

Retrieving only the datasets needed is cheaper — retrieve cost scales with
the number requested (K), not the file total (N). Selecting ~10% of a
many-dataset file cost ~10× less than retrieving all of it. **Effect:** filtering by
tag/blob pattern at retrieve time avoids pulling the whole bundle. (Ingest-side
dataset selection is available via `dataset_filter` include/exclude glob
patterns in the OMNI file — see `references/omni_selective.md` — but the assimilator
still ingests whole datasets.)

## Practice 4 — Per-byte scaling is fine; it's objects/chunks that hurt

clio-core scales gracefully with data *size* (read overhead is a constant ~3×
cold / ~6–8× warm from 256 MB to 2 GB) but badly with object/chunk *count*.
**Effect:** large contiguous datasets are the friendly case; high object counts
are the hostile one. The file's structure (fewer objects) matters, not its total
size.

## API gotchas (when ingest is actually warranted)

- Routing is by the `src` **protocol prefix**, not the `format` field:
  `hdf5::` → semantic per-dataset ingest (one tag per dataset); `file::` →
  opaque whole-file byte chunking. `format=` is cosmetic and ignored for routing.
- Read array data back via the CTE data plane (`Tag.GetBlob`), **not** the CEE
  `context_retrieve` text layer — the latter is UTF-8 and raises
  `UnicodeDecodeError` on binary. Order `chunk_N` blobs by numeric index.
- The assimilator ingests whole datasets only (*which* datasets can be chosen
  with `dataset_filter`, see `references/omni_selective.md`); it does **not** read HDF5
  attributes, and hyperslab/attribute reads are not available through it.

## Common pitfalls

- **`src="file::"` with `format="hdf5"`** → silently gets the opaque binary
  chunker (no per-dataset structure).
- **Bundling a many-small-dataset file as-is** → minutes of per-object overhead.
  Consolidation or native reads avoid it.
- **Expecting attributes / hyperslab reads** → not supported by the assimilator.
