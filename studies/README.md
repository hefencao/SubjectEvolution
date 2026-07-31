# Study directory

Each study keeps design, protocol, immutable evidence, and one declarative
`workflow.toml`.  Commands are not executable files.

Inspect a study before execution:

```text
se-study show studies/<study>
```

Execute one named step with explicit registered overrides:

```text
se-study run studies/<study> <step> --backend gpu --seeds 1,2,3
```

Use `--dry-run` to render the final argv without execution. Every active study
must provide a `pack-results` step; checkpoint inclusion is an explicit boolean
parameter rather than an environment variable.
