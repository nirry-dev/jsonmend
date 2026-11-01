# Security Policy

## Reporting a vulnerability

Please report security issues privately to **info@nirry.net** rather than in a
public issue. Include the input that triggers the problem and what you observed.
You'll get an acknowledgement, and a fix or a clear explanation.

## Scope notes

jsonmend reads untrusted text (model output), so it is written defensively: the
reader makes bounded progress on every input, closes rather than loops on
truncation, and never executes or evaluates what it reads. It returns plain
Python data and strict JSON — it does not touch the network or the filesystem on
its own (the CLI only reads the file or stdin you point it at).

## Supported versions

Fixes land on the latest release.
