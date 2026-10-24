---
id: shell.gh-releases
section: capabilities
when: {"tools": ["shell_bash"]}
---
For published releases, inspect live GitHub records rather than local tags:
`gh release list --repo OWNER/REPO --limit 20 --json tagName,publishedAt,isDraft,isPrerelease`
and `gh release view TAG --repo OWNER/REPO --json tagName,publishedAt,isPrerelease,body,url`.
`/releases/latest` selects the latest stable release, not the newest
prerelease. Exclude drafts and report stable and prerelease channels separately.
