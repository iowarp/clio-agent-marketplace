---
name: copernicus-data
title: Copernicus Data
description: Get Copernicus Marine products (reanalysis, analysis and forecast, altimetry, sea surface temperature) and Climate Data Store datasets (ERA5 and others) as files with provenance - searching, describing, estimating, subsetting, following jobs, and the product and licence behind each file.
keywords:
- level:L2
- copernicus
- cmems
- cds
- era5
---

# Copernicus data

The Copernicus server is copernicus-mcp run as its maintainers ship it. Its tools
fetch files; analysis happens in scripts or other servers on the files it
returns.

## Copernicus Marine (`marine_*`)

- **Finding a product.** `marine_search_datasets` (or `marine_search_products`
  and `marine_search_groups` to browse) takes the variable, region and period
  in words. A reanalysis suits past states and climatologies, an analysis and
  forecast product recent days, and an observation product questions about
  observations; which kind was used, and why, shapes how the numbers read.
- **Its description.** `marine_describe_dataset` and `marine_get_coordinates`
  give the variables, units, depths, time span and resolution. Names and ranges
  from memory are often wrong.
- **Size before fetching.** `marine_estimate_subset` sizes a box, depths, period
  and variables. A large estimate shrinks with fewer variables, depths or days,
  or a coarser product, before `marine_subset_dataset` moves data.
- **Jobs.** A subset may run asynchronously: `marine_check_status` reports it,
  and `marine_get_files` / `marine_list_files` give the paths. Jobs survive
  restarts; `marine_cancel_subset` stops one that is no longer needed.

## Climate Data Store (`cds_*`)

`cds_search_datasets`, `cds_describe_dataset`, `cds_apply_constraints`,
`cds_estimate_request`, `cds_submit_request`, `cds_check_request_status` and
`cds_download_request_result` cover a request from search to download. The dataset's
own constraints define which requests are valid. Each dataset's licence is
accepted once by the account holder on its CDS page: `cds_list_licences` shows
which are accepted. A request refused for an unaccepted licence names the
dataset whose licence the person needs to accept. `cds_cancel_request` stops a
request that is no longer needed.

## Accounts

The accounts belong to the Copernicus connector. A tool that reports a missing
account, or no `cds_*` tools listed, means the person needs that account
(Copernicus Marine or the CDS token), which is added in the Copernicus
connector's settings. Credentials do not belong in the conversation.

## Provenance

Every file comes with the product id, version, subset and licence. They travel
with the file into the provenance of whatever is derived from it, and the
product and its licence identify the source wherever its numbers are reported.