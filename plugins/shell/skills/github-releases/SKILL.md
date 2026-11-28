---
name: github-releases
title: Read published GitHub releases
description: Use when a question is about a repository's published releases or release channels (latest stable, prereleases, what shipped when).
---

# Published GitHub releases

Live GitHub records show what was published; local tags may not:

- `gh release list --repo OWNER/REPO --limit 20 --json tagName,publishedAt,isDraft,isPrerelease`
- `gh release view TAG --repo OWNER/REPO --json tagName,publishedAt,isPrerelease,body,url`

`/releases/latest` selects the latest stable release, not the newest prerelease.
Drafts are unpublished, and the stable and prerelease channels answer different
questions.
