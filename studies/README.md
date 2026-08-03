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


## External result storage

Result bundle outputs use workflow parameter type `result-path`. Configure the
project once with `se-study config --set-result-dir /absolute/external/path`.
Relative bundle filenames then resolve under that directory; paths inside the
project are rejected. The ignored `.se-workspace.toml` pointer is local state
and is not included in release archives.

## External patch storage

Configure a project-external patch directory once with
`se-study config --set-patch-dir /absolute/external/path`. Delivery Git commands
must apply `${patch_dir}/<actual-patch-name>` rather than a bare patch filename.
For the bootstrap patch that first introduces this option, define `PATCH_DIR`, apply
the prefixed patch, and persist the setting immediately afterward through the patched
source. The same ignored `.se-workspace.toml` stores both directory pointers.
