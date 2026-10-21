---
id: seismic-waveform-review.guidance-2
section: domain
---
If any returned child result includes `NEXT_EXPERT: visualization`,
`NEXT_ACTION: plot_sac_traces`, `DO_NOT_FINALIZE_BEFORE_VISUALIZATION: true`,
`.sac`, or "No PNG plot artifact", the next `expert_handoffs` row must target
`visualization` with the exact SAC path. Do not produce a final answer from
that state. The final answer must cite an observed `FINAL_ARTIFACT:` PNG path or
equivalent Visualization result proving `sac_plot_traces` ran.

After Visualization returns `FINAL_ARTIFACT:` or an equivalent successful PNG
artifact path, the workflow is complete. Do not delegate to Data, Analysis, SAC,
or Visualization again from that state. Return a normal user-facing final answer
that summarizes what was done, cites the SAC path and PNG artifact path, and
mentions any NDP staging blocker or EarthScope fallback caveat already observed.
