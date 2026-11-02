# Hyokeisan grid snapshot value experiment, 2026-11-02

The experimental Kotoba grid kernel now constructs a bounded versioned vector
value (magic, version, 16 integer cells) and can restore it into a current grid.
Wrong length, magic or version is refused and preserves the current value.
This representation is not a committed storage schema, byte encoding, migration
format, atomic disk write, or browser/OS persistence implementation. It does
not inspect or alter existing user data.

Source SHA-256: `6740f8ba2bc588c552a52e6ce5802befd74538746e1cc594bd75f84205a586db`.
Amu d4d6841f129d846db13393a469645e1ca91fb568 macOS ARM64 native CLI returned
0. The same source compiled by the selfhost full root to wasm32-browser
(SHA-256 `dd099de9504cc42f74c03e11cb7cc63a6fe24663f413ae02c98e27d47efe9dea`)
returned `:status :ok :result 0` in Chrome 156.0.8078.74 using the Amu Worker
harness with no granted wires. Mutating the row stride or accepting an unknown
version independently returned result 1. The browser harness reports normal
process exit for both results; `scripts/check-grid-wasm.py` explicitly checks the
guest result. No QEMU or Itonami OS execution is claimed.

Reproduce with `python3 scripts/check-grid-wasm.py /path/to/amu /new/output/directory /path/to/Chrome`
on macOS ARM64, using the pinned Amu revision. UI, save/reload, concurrent writes,
crash recovery, portable byte encoding, old-origin import, QEMU and release
qualification remain open.

## Cross-target probe

The same source compiled with the same full root to x86_64-linux static ELF
(SHA-256 `9336c0d932c0418d6e1c10924f34defee5828b1ec619a00c28d06013c1d7e4e7`).
Running it through an existing amd64 container on an ARM64 Podman VM failed
before the program ran: `kexe-runtime: resource limit setup failed`, exit 1.
The cause is unconfirmed; this does not test Itonami OS.

The `x86_64-aiueos-user-v1` compile of that same source refused `grid-new`
(vector return, `rt=4`) with `E7102 unsupported object profile; detail 1`.
No Itonami OS or QEMU execution was performed. Browser and OS target parity
therefore remains open.
