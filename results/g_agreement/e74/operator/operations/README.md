# E74 local operations layer

This is a separate CPU-built derivative of the scientific runtime published in commit473d9f9b. The parent image/config ID is `sha256:447fe0821f2ca4fb22daa5a06ade52edad3c710d22d2ef1e6852b69afeeb65e0`. Its exact layers are preserved. The resident-v5 science archive, frozen inputs, author runtime, plugin and all Python package locks are unchanged.

`OS_LOCK.json` fixes26 Debian packages by version, architecture, filename, byte size and SHA256 matched to the signed Debian package indexes. The requested tools are OpenSSH server/SFTP/client, rsync, procps, tini and curl. Bash, setsid, timeout, coreutils, tar and gzip already exist in the parent. The local Debian package bundle is5,087,416 bytes. Build networking is disabled; the installer receives only the local verified package closure. Rebuild from the frozen files, not a new apt resolution.

`SCIENTIFIC_FILES.json` fixes244 files from the parent: the Python executable, author source and recipe files, all installed distribution METADATA files and13 plugin Python sources. `verify_ops.py` checks those bytes, installed OS versions, tool availability, dpkg consistency and absence of baked host/authorized keys. The parent-layer prefix is also checked. The same original CPU package/import checks are rerun in the derivative; no engine or plugin registration is invoked.

## Rebuild locally

Load the verified scientific-runtime Docker archive if the exact parent image is not already present. Use the matching26 `.deb` files from the frozen local context bundle (receipt in `BUILD_RECEIPT.json`). The build helper verifies every package and the exact parent config ID before creating its local alias:

```sh
python3 results/g_agreement/e74/operator/operations/build_local.py \
  --debs /absolute/path/to/frozen/debs \
  --context /absolute/path/to/new/context \
  --metadata /absolute/path/to/build-metadata.json
```

The default local tag is `codex/e74-author-ops:20261027`. `BUILD_RECEIPT.json` records the final derived image ID and CPU results. `LOCAL_IMAGE_MANIFEST.json` records content-hashed OCI metadata extracted from a local Docker-save stream; this is not a registry-available manifest. The full operations image is retained in local Docker; the small offline operations context and original scientific image archive provide a separate rebuild route. Image timestamps are not claimed to reproduce bit-for-bit across rebuilds; all software/source inputs are pinned and validated. A rebuilt image needs its own identity receipt. The local tag and config ID are not an available registry pull reference.

## Start and control

The entrypoint is `tini -g -- python /opt/e74-ops/start.py`. It starts only an SSH daemon on container port22; it never starts a model, downloads weights or launches E74. Supply `SSH_PUBLIC_KEY` at launch. The parser accepts plain OpenSSH public keys, discards comments, rejects options/private-key text and fails closed when missing or invalid. Authorized keys and freshly generated host keys live under `/run/e74-ssh`, not in the image. Package-installation-generated host keys are deleted within the same build step before its layer is saved. Password and interactive authentication, forwarding and user environment files are disabled. Root public-key access is intentional for I-2's existing operator; no password or private key is embedded.

`test_control.py` exercises Mac-to-local-container public-key SSH, PID1 native identity, SFTP/rsync round trips, setsid/process-group signals/timeout, rejection of unknown keys, unique host keys and graceful container stop. It binds only to127.0.0.1, creates temporary test keys outside all build contexts and removes the keys and containers afterward. The test is CPU-only and explicitly checks that no GPU device request exists.

## Concrete deployment choice and remaining gate

Use this full-SSH operations image as the Runpod custom image, with port22/tcp, a launch-time public key and the agreed workspace/NVMe mounts. Retain its entrypoint; provider control-plane overrides must be reviewed by I-2. Upload the unchanged resident-v5 package and use the established Mac SSH/SFTP/rsync operator. All scientific phase gates and provider hard stops remain I-2's responsibility.

The selected distribution route is a registry pull of the final derived image. No registry publication has occurred. Metadata-only Docker credential-helper enumeration returned no saved registry accounts; no credential value was requested or printed and no account/token was tested. A subsequent metadata-only GitHub CLI check confirms the active github.com account `guivff` is authenticated, with scopes `gist, read:org, repo, workflow`; it lacks `write:packages` and `read:packages`. The concrete proposed destination is private `ghcr.io/guivff/e74-author-ops:20261027`, pending I-2 destination/auth approval. It has not been created or tested. The existing CLI connection does not establish GHCR upload or private-pull capability. No token values were requested or printed. An approved registry destination/authentication and explicit publication authorization are still needed. [GitHub Container registry authentication](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry). Once published, capture and verify its real registry manifest digest and provider pull identity; do not pass the local config ID as a purported remote manifest.

Image pull/unpack/control setup must fit the existing900-second allowance and the whole-E74 budget. The exact4B200 quote and host driver/CUDA13.4 compiler compatibility remain unverified. After admission, use the unchanged50-fixture statistics-only smoke (seed20261027; excludesE66): (exact>=0.15 OR median token-set Jaccard>=0.50) AND grammar violations<=10%. No retuning, capture/readout/judge authorization or B300 implementation is supplied by this CPU layer.
