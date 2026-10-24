---
name: edit-markdown-html
description: Create or revise Markdown and non-executing HTML document artifacts while preserving semantic structure, links, accessibility, and review anchors. Use for .md, .markdown, static .html/.htm, and lightweight rich document outputs; transition executable HTML to Live Web.
---

# Edit Markdown and Static HTML

1. Confirm the exact artifact version and read the entire source before changing a selected region.
2. Preserve heading hierarchy, link targets, alt text, table headers, IDs used by review anchors, and frontmatter keys not owned by the request.
3. Keep HTML static. Do not add scripts, inline event handlers, active forms, remote execution dependencies, or navigation tricks. If interaction is required, explicitly transition the artifact to Live Web and obtain its normal consent.
4. Use semantic HTML before presentational containers. Keep print styles useful so PDF rendition remains legible.
5. Validate Markdown structure or HTML parsing and inspect links/assets that can be checked locally.
6. Save the canonical source and allow CLIO to mint a new artifact version.

See [document-quality.md](references/document-quality.md) for completion checks.
