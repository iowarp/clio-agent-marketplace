---
name: dtype_mapping_rules
title: Dtype Mapping Rules
description: Apply safe dtype mapping rules for HDF5 to Parquet conversion.
---

Use this skill when deciding how scientific source dtypes map into Parquet.
Preserve float64 and integer arrays when safe, preserve strings as strings, and
handle datetime logical types explicitly.

Skip or require confirmation for dtypes that are lossy, unsupported, or likely
to hide scientific meaning.
