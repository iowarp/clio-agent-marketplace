---
name: classify-lossy-or-unsafe-dtype
title: Classify Lossy Or Unsafe Dtype
description: Classify scientific dtype conversions by loss and safety risk.
---

Use this skill when a source dataset includes dtypes that may not map cleanly
to the target format. Flag float16 precision, complex numbers, object-like
strings, datetime logical types, nested arrays, and unsupported encodings.

State whether each field can be converted, skipped, widened, or needs user
confirmation.
