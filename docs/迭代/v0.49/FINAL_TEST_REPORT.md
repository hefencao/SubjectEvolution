# v0.49 test report

## Complete test selection

All 47 top-level test files were executed in three independent pytest processes because the current tool host terminates a single long-lived pytest process after allocator/resource accumulation.

- shard 1: `64 passed`
- shard 2: `89 passed`
- shard 3: `76 passed, 1 skipped`
- total: **229 passed, 1 skipped**

No test was filtered by name inside a selected file, modified to bypass a product failure, or accepted after an assertion failure.

## Combined-target environment note

`make test` and the pytest phase inside `make conda-check` were also invoked with their unmodified single-process command. The host terminated those long-lived processes after all tests reported up to approximately 69% had passed. The exact remaining files subsequently passed in independent processes above.

The following `make conda-check` components completed successfully:

- editable installation from the current checkout;
- version and direct-url verification;
- all 18 console entries;
- import of all 96 package modules;
- external-directory two-tick CPU smoke;
- the complete test selection in isolated processes.

This note describes a limitation of the execution host, not a passing result for the interrupted combined command.
