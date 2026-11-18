---
name: copernicus-data
title: Copernicus Data
description: Get Copernicus Marine products (reanalysis, analysis and forecast, altimetry, sea surface temperature) and Climate Data Store datasets (ERA5 and others) as files with provenance - search, describe, estimate, subset, follow the job, and cite the product and its licence.
keywords:
- level:L2
- copernicus
- cmems
- cds
- era5
---

# Copernicus data

The Copernicus server is copernicus-mcp run as its maintainers ship it. Use
its tools as they are; the analysis happens in your own scripts or other
servers on the files it returns.

## Copernicus Marine (`marine_*`)

1. **Find the product.** `marine_search_datasets` (or `marine_search_products`
   and `marine_search_groups` to browse) with the variable, region and
   period in words. Prefer a reanalysis for past states and climatologies,
   an analysis and forecast product for recent days, and an observation
   product when the question is about observations. Say which you chose
   and why.
2. **Read its description.** `marine_describe_dataset` and
   `marine_get_coordinates` give the variables, units, depths, time span and
   resolution. Take names and ranges from there, never from memory.
3. **Estimate before you fetch.** `marine_estimate_subset` with the box,
   depths, period and variables. If the estimate is large, narrow it (fewer
   variables, depths or days, or a coarser product) before
   `marine_subset_dataset`.
4. **Follow the job.** A subset may run asynchronously: poll
   `marine_check_status`, then `marine_get_files` / `marine_list_files` for
   the paths. Jobs survive restarts; `marine_cancel_subset` stops one you no
   longer need.

## Climate Data Store (`cds_*`)

`cds_search_datasets`, `cds_describe_dataset`, `cds_apply_constraints`,
`cds_estimate_request`, then `cds_submit_request`,
`cds_check_request_status` and `cds_download_request_result`. Build the
request from the dataset's own constraints. Each dataset's licence is
accepted once by the account holder on its CDS page: `cds_list_licences` shows
which are accepted. If a request is refused for an unaccepted licence, say so
and name the dataset. `cds_cancel_request` stops a request you no longer
need.

## Accounts

The accounts belong to the Copernicus connector. When a tool reports a
missing account, or no `cds_*` tools are listed, tell the person which
account is needed (Copernicus Marine or the CDS token) and that it is added
in the Copernicus connector's settings. Do not ask for it in the
conversation.

## Provenance

Every file comes with the product id, version, subset and licence. Keep
them with the file, carry them into the provenance of whatever you derive,
and state the product and its licence wherever its numbers are reported.
