# Windows Classroom release

Target only Windows 10/11 x86-64. Stage the private layout documented in
`docs/offline-classroom.md`; never install runtimes globally or add them to PATH.

## One-command build on Windows Server

Install Python 3.13 x64 with pip and Inno Setup 6 on a 64-bit Windows Server.
Git is optional and is used only to record the commit in release metadata. From
the repository root in PowerShell, run:

```powershell
.\build-windows-classroom.ps1 -ReleaseVersion "6.0.0-classroom.1"
```

The script runs the tests, downloads and checksum-verifies the pinned Python,
Node.js, Go, llama.cpp, and Qwen GGUF artifacts, stages dependencies, performs
real runtime and model smoke tests, and creates:

```text
.classroom-build\6.0.0-classroom.1\release\thonny-classroom-6.0.0-classroom.1-windows-x64-setup.exe
```

If staging completed but a smoke test was interrupted, rerun the same command;
it resumes the verified staged bundle without downloading or reinstalling it.
Use `-Force` when you intentionally want to rebuild the same release version
from scratch. Cleanup is restricted to that version's directory under
`.classroom-build`. Both `.classroom-build/` and `.classroom-cache/` are ignored
by Git, as are all `*.gguf` files. The first Qwen load may take several minutes
on a CPU-only server and prints a progress message before inference begins.

The release bundle is assembled only on the build machine. `stage_bundle.py`
downloads the pinned Python, Node.js, Go, llama.cpp, and Qwen artifacts, verifies
their SHA-256 digests from `artifacts.json`, and writes them under the ignored
`app/` directory. The GGUF model and downloaded runtime archives must never be
committed.

Run the authoritative release gate from the repository root:

```
python packaging/windows/classroom/verify_release.py app checksums.json
```

`verify_bundle.py` checks only the basic directory layout and file hashes; it is
not sufficient for a release. Only create an installer after
`verify_release.py` and `smoke_bundle.py app --with-model` succeed. Keep
downloaded archives outside Git. Include the exact Node.js, Go, llama.cpp, Qwen,
and Thonny notices in `app/licenses/`.

## Manual GitHub Actions release to S3

The `Release Windows Classroom installer to S3` workflow is manual-only. It
downloads and checksum-verifies the model during the job, smoke-tests the private
runtimes and real model, builds the Inno Setup installer, and uploads the
installer, its SHA-256 file, `COMPONENTS.json`, and `release.json` to:

```
s3://<S3_BUCKET>/<S3_PREFIX>/<release_version>/
```

Create a protected GitHub Environment named `release` (an approval rule is
recommended) and add these environment variables:

- `AWS_REGION`: bucket region, for example `us-east-1`
- `S3_BUCKET`: bucket name only
- `S3_PREFIX`: optional key prefix, for example `classroom/releases`
- `AWS_ROLE_TO_ASSUME`: ARN of the GitHub Actions release role

Use GitHub's OIDC provider for AWS; do not create long-lived AWS access-key
secrets. Restrict the role's trust policy to this repository and the `release`
environment (`repo:OWNER/REPOSITORY:environment:release`). Its S3 policy only
needs `s3:PutObject` and `s3:GetObject` on
`arn:aws:s3:::BUCKET/PREFIX/*`. Bucket listing is not required.

From GitHub's **Actions** page, select the workflow, choose **Run workflow**, and
enter a release version. Existing version keys are rejected unless the operator
explicitly selects `allow_overwrite`.
