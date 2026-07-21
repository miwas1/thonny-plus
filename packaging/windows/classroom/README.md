# Windows Classroom portable release

Target only Windows 10/11 x86-64. Stage the private layout documented in
`docs/offline-classroom.md`; never install runtimes globally or add them to PATH.

Create `checksums.json` from the pinned publisher checksums, with paths relative
to the staged `app` directory, then gate the release:

```
python verify_bundle.py app checksums.json
```

Only create the portable ZIP after this command succeeds. Keep all archives,
executables, and GGUF files outside the source tree. Include the exact Node.js,
Go, llama.cpp, Qwen, and Thonny notices in `app/licenses/`.
