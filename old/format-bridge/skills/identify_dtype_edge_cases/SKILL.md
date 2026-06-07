---
name: identify_dtype_edge_cases
title: Identify Dtype Edge Cases
description: Identify source datasets that require conversion policy decisions.
---

Use this skill during source inspection. Look for NaNs, complex values,
float16, datetime-like integers, strings, nested structures, ragged arrays, and
compression or chunking metadata that could affect conversion.

Return edge cases as explicit policy inputs.
