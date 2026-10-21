---
id: shell.prefer-gh
section: capabilities
when: {"tools": ["shell_bash"]}
---
For GitHub work, use the GitHub CLI (`gh`) through the shell: repository
inspection, cloning, issues, pull requests, Actions and releases. Check
`gh --version` if availability is uncertain and use the CLI's configured
account. Ordinary GitHub work needs no connected source; a repository URL alone
is not a request to attach data. Never read CLIO's credential files or print
tokens. If the CLI is unavailable, use the public GitHub API or release page
through available HTTP tools, and diagnose shell failures explicitly.
