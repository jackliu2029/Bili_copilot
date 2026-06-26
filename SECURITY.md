# Security Policy

Bili_copilot may optionally use a local Cookie file for authenticated subtitle access.

Security rules:

- Do not commit Cookie files.
- Do not paste Cookie values into issues, pull requests, chats, logs, README, or output files.
- Keep Cookie files outside the project directory.
- Use `--cookie-file` only with a local file path.
- The project must not automatically read browser Cookie stores.
- The project must not print Cookie values.
- The project must not include Cookie values in exported content packages.

If a secret was committed accidentally, rotate or invalidate it immediately and remove it from Git history before publishing further.
