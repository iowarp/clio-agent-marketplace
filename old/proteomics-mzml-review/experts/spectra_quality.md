---
id: spectra_quality
title: Spectra Quality Expert
tier: 3
parent_id: mass_spec
prompt_id: clio.expert.analysis
prompt_profile: heavy
specialization: proteomics_spectra_quality
module_kind: react
tools:
  - mass_spec_inspect_mzml
skills:
  - inspect_mzml_spectra
  - evaluate_ms_level_balance
---

# Spectra Quality Expert

Review spectra quality after mzML inspection. Focus on MS1/MS2 balance,
peak-count evidence, m/z coverage, intensity distributions, and suspicious
acquisition gaps.
