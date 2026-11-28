---
name: connect-data
title: Connect research data sources
description: Use when the user asks to connect data, or when needed inputs are absent after inspecting supplied references and workspace folders. External sources connect through CLIO's private setup UI.
---

# Connect data

Supplied attachments, references and the current workspace folders are already
readable with the file tools. A primary workspace folder is already input; an
empty connected-source list does not mean its files are missing. A failed read
reports an access or runtime error; reconnecting that folder does not fix it.

Connecting a source is for data that is elsewhere, or when the person wants a
source connected.

`connected_data_status` returns the inventory of approved workspace folders,
attached sources, and signed-in provider accounts. It returns status, not a
setup control. A child session without this tool has no setup path; setup
happens in the main session. Its `storage` block gives the free bytes where
downloads are kept and each source's bytes on disk. A download larger than the
free space fails; `connected_data_release` frees older copies of a source (the
current copy stays readable), and a range read fetches only the part needed.

National Data Platform work is covered by `work-with-ndp`, when this agent has
it (the `ndp` plugin). An NDP dataset someone attached with **Attach > NDP**
is an ordinary connected source here: the tools below list, open and download
it. Without the `ndp` plugin there is no NDP catalog search or Endpoint
connection; Attach > NDP and the NDP agent still are. Private selection
configuration comes only from the setup UI.

When an account needs sign-in, its returned `login_action` is the action of an
ordinary A2UI Button; the active catalog gives the exact component shape. The
person sees and clicks this control in the answer, and the existing private
account flow opens. It never passes a credential to the agent. An action shown
only in Activity is easy for the person to miss.

`connected_data_connect` attaches a remote source the person asked to attach. A
URL alone is not a request to connect a source. A new connection passes through
the session permission gate; bypass can approve it automatically, while explicit
deny/ask rules still apply. An already-approved identical source is reused.
Registration, authentication and a successfully linked file index are separate
states, and the returned state says which was reached. After sign-in, a retried
connection builds the linked index.

Ordinary GitHub inspection, releases, cloning and development go through `gh` or
`git` in the normal shell with its configured account. The shared GitHub shell
prompt explains release evidence and stable/prerelease distinctions. A repository
URL or a request for a public release is not a request to connect a source.
Public API/browser reads also give public facts when the CLI cannot perform the
read.

The connected-source path is for repository data attached to the workspace. Its
private CLIO account, repository/folder grants and source working-copy
review/publication rules remain independent of ordinary shell work.

The person selects a source and, when required, signs in in their browser.
Sign-in runs independently of the agent; only the outcome and approved data
references are returned. The UI's info icon explains this privacy boundary.
Passwords, access tokens, authorization codes, callback URLs and OAuth client
configuration do not belong in chat. Sign-in through shell, HTTP or browser
tools, and reading CLIO's private credential files, bypass that boundary.

Setup completes on the person's side; polling does not speed it up, and
`connected_data_status` shows the result once they return. Registration alone
does not mean files are available; the approved local path exists only after
materialization is ready. Disconnected sources cannot access upstream data;
their retained local copies are historical evidence.

Read only is the default. Working copy preserves an immutable baseline, and the
person reviews selected changes before they apply upstream. Write enabled exists
only where the selected host supports a genuinely writable folder; synchronization
and filesystem drivers are not substitutes. Refresh, apply changes, disconnect,
remove a copy, and delete upstream data are different actions. Permission changes
and reviewed writes go through the trusted UI.

All paths belong to the connected CLIO named in the picker. **Upload desktop
folder** sends a desktop folder to a remote CLIO with its structure preserved.
Missing distributor setup is a provider prerequisite; registering an OAuth
application is not something an ordinary user does.