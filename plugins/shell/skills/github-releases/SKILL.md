---
name: github-releases
title: Read published GitHub releases
description: Use when a question is about a repository's published releases or release channels (latest stable, prereleases, what shipped when).
---

# Published GitHub releases

Inspect live GitHub records rather than local tags:

- `gh release list --repo OWNER/REPO --limit 20 --json tagName,publishedAt,isDraft,isPrerelease`
- `gh release view TAG --repo OWNER/REPO --json tagName,publishedAt,isPrerelease,body,url`

`/releases/latest` selects the latest stable release, not the newest prerelease.
Exclude drafts, and report the stable and prerelease channels separately.
