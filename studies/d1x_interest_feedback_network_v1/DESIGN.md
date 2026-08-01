# D1-X design boundary

For a directed assessment `A -> B`, material sent from A to B is recorded as A's realized giving, while material later received by A from B is recorded as A's realized return. At the end of a bounded window, the directed relation value moves toward `received / (given + received)`, scaled by evidence confidence. Reciprocal balanced exchange therefore produces positive bilateral values instead of being collapsed to zero net flow.

This first implementation deliberately excludes protection, information value, conflict assistance and downstream survival attribution. Those consequences require separate observable ledgers and shared-checkpoint neutralization before Epoch 1 can be considered.
