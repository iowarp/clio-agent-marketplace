---
name: parquet
title: Parquet
description: Use for Apache Parquet files and partitioned Parquet datasets - what the footer states (schema, row groups, column statistics), physical versus logical types (timestamps with unit and UTC flag, decimals, unsigned integers, float16, dictionary, nested lists and structs), hive partitioning, bounded scans with pyarrow.dataset or DuckDB, write options, and the limits of the parquet tools.
keywords:
- level:L2
- parquet
- format
---

# Parquet

Parquet describes itself: every file ends with a footer that holds the schema,
the row groups and per-column-chunk metadata. Read that before reading data,
and report what the footer states separately from what you computed.

## Layout

- A file is `PAR1`, the row groups, the footer, the footer length, `PAR1`.
  Readers fetch the footer first, so schema and counts are cheap.
- **Row groups** hold a horizontal slice of rows. Inside each, every column is
  a **column chunk** made of **pages** (an optional dictionary page, then data
  pages). Row-group size decides how much a filtered scan can skip.
- **Column-chunk metadata** gives the physical type, codec, encodings, sizes
  and optional **statistics**: min, max and null count per row group.
  Statistics are hints for skipping, not results: writers may omit them,
  truncate long binary values, and leave NaN out of float min/max, so a column
  whose statistics look clean can still hold NaN. Count nulls and NaNs from the
  data when the answer depends on them.
- Key-value metadata in the footer may carry the writer (`created_by`), an
  embedded Arrow schema (pyarrow writes one by default) and producer notes.

Inspect with pyarrow: `pq.ParquetFile(path).metadata` (rows, row groups,
`created_by`, `format_version`), `.schema` (the Parquet schema with logical
types), `.schema_arrow`, and `metadata.row_group(i).column(j)` for one chunk's
type, codec and statistics. DuckDB offers `parquet_schema('f.parquet')` and
`parquet_metadata('f.parquet')`.

## Physical and logical types

Physical types are BOOLEAN, INT32, INT64, INT96, FLOAT, DOUBLE, BYTE_ARRAY and
FIXED_LEN_BYTE_ARRAY. A logical type annotation gives the meaning; always
report both when a type matters.

| Logical type | Stored as | Check |
|---|---|---|
| Timestamp | INT64 with unit MILLIS, MICROS or NANOS and `isAdjustedToUTC` | `isAdjustedToUTC=true` is an instant in UTC; `false` is a local wall-clock time with no zone. A named time zone is not part of Parquet; pyarrow restores it from the embedded Arrow schema, other readers may show UTC. |
| INT96 timestamp | INT96 | A legacy encoding from older writers (Impala, Spark); readers convert it, usually to nanoseconds. |
| Date, Time | INT32 / INT64 | Date is days since the epoch; Time has its own unit and UTC flag. |
| Integer(bitWidth, signed) | INT32 / INT64 | Unsigned 64-bit values are stored in INT64 with `isSigned=false`; a reader that ignores the annotation shows negative numbers above 2^63 - 1. |
| Decimal(precision, scale) | INT32, INT64, FIXED_LEN_BYTE_ARRAY or BYTE_ARRAY | Exact; converting to float loses exactness. Report precision and scale. |
| Float16 | FIXED_LEN_BYTE_ARRAY(2) | A recent addition; older readers see two raw bytes. |
| String, Enum, JSON, UUID | BYTE_ARRAY / FIXED_LEN_BYTE_ARRAY | Bytes without the String annotation are binary, not text. |
| List, Map, struct (group) | nested groups with repetition and definition levels | Leaf columns have dotted paths such as `col.list.element`; statistics exist per leaf, not per list. |

**Dictionary encoding** is a storage choice per column chunk (pyarrow uses it
by default), not a type: readers decode to plain values unless asked
(`pq.read_table(..., read_dictionary=[...])`). An Arrow dictionary or pandas
categorical column round-trips through the embedded Arrow schema.

## Partitioned datasets

A directory tree such as `root/key=value/.../part-*.parquet` is **hive
partitioning**: the partition columns live in the directory names, not in the
files. Their types are inferred by the reader and readers differ (pyarrow may
read an integer partition as int32 where DuckDB reads BIGINT), so state the
type you used. Check that every file has the same schema; a dataset reader
unifies or fails, and files can disagree.

## Bounded reads

Read the footer, then only the columns and rows you need:

```python
import pyarrow.dataset as ds
d = ds.dataset(path, format="parquet", partitioning="hive")   # a file or a directory
d.schema
d.count_rows(filter=ds.field("site") == "a")
d.to_table(columns=["time", "value"], filter=ds.field("value") > 0)
for batch in d.to_batches(columns=["value"], batch_size=65536): ...
```

`pq.ParquetFile(path).iter_batches(batch_size=..., columns=[...])` and
`.read_row_group(i, columns=[...])` stream one file. With DuckDB:
`SELECT ... FROM read_parquet('root/**/*.parquet', hive_partitioning = true)
WHERE ... LIMIT ...`. Run these as scripts through `shell_bash` with
`uv run --no-project --with pyarrow` (or `--with duckdb`), and keep the
script in the workspace.

## Writing

When you write Parquet, choose and report: compression (pyarrow's default is
snappy; zstd is smaller), row-group size, dictionary use, statistics (on by
default), the format version (pyarrow writes `2.6`, which keeps nanosecond
timestamps), and timestamp coercion. Put provenance in the schema's key-value
metadata (`schema.with_metadata({...})`): the source path and checksum, the
conversion script and any lossy or skipped fields. Read the file back and
compare row counts, schema and per-column checksums before calling it done
(see `convert-scientific-data` when converting from another format).

## The parquet tools

The clio-kit `parquet` server works on one file at a time and caps each
response at about 16 KB:

- `summarize_tool`: Arrow schema, row count, row-group count, file size.
- `read_slice_tool`: rows `start_row` to `end_row` with optional `columns`
  and a JSON filter (`{"column": "x", "op": "less", "value": 1}`; ops
  `equal`, `not_equal`, `less`, `less_equal`, `greater`, `greater_equal`,
  `is_null`, `is_valid`, `is_in`; combine with `and`, `or`, `not`). It loads
  the selected columns of the whole file before slicing, and the filter
  applies only inside the slice; pass `columns` on large files.
- `get_column_preview_tool`: up to 100 values of one column per call.
- `aggregate_column_tool`: `min`, `max`, `mean`, `sum`, `count`, `std` or
  `count_distinct` of one column, optionally filtered or row-bounded.

They do not read partitioned directories, footer statistics or logical-type
annotations; use pyarrow or DuckDB for those, and for anything larger than a
quick look.
