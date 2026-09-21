---
name: windows-store-msix
description: >-
  Plan and implement MSIX packaging and Microsoft Store submission for the
  existing Windows PyInstaller GUI build. Use when working on MSIX, AppxManifest,
  Partner Center, Windows Store, MakeAppx, or Store CI packaging.
audience: cursor-agent
note: >-
  Cursor agent playbook only. Not read by Windows, MakeAppx, or GitHub Actions.
  Packaging lives in packaging/msix/ and .github/workflows/build_gui.yml.
---

# Windows Store / MSIX

## Goal

Ship a Store-ready MSIX (or msixbundle) built from the current Windows PyInstaller output, then submit via Partner Center. Keep `CIBMangoTree_windows.zip` for GitHub Releases.

## Repo facts

- Windows build: `.github/workflows/build_gui.yml` matrix entry `Windows` / `windows-2022`
- Artifact today: onedir under `dist/CIBMangoTree` → zip `CIBMangoTree_windows` and MSIX `CIBMangoTree_windows_msix`
- MSIX pack: `packaging/msix/AppxManifest.xml` + `MakeAppx` in `build_gui.yml` (Windows only)
- Store upload from `release.yml` (`publish_msix` job) on stable tags
- macOS already has signing/notarization patterns for secrets — mirror the secrets approach, not the Apple tooling

## Phased workflow

### Phase 0 (no Partner Center login)

1. Research with **microsoft-learn** MCP (`microsoft_docs_search` / `microsoft_docs_fetch` / `microsoft_code_sample_search`)
2. Draft `AppxManifest.xml` placeholders (Name, Publisher, Version, capabilities)
3. Design CI step after PyInstaller: MakeAppx (or equivalent) → upload `.msix` artifact
4. On a Windows VM: sideload a test MSIX from local `dist/CIBMangoTree`, run `--noop`

### Phase 1 (login available)

1. Align manifest Publisher/Identity with Partner Center exactly
2. Obtain Store upload / signing material per Microsoft docs for the account type
3. Store secrets in GitHub Actions (never commit)

### Phase 2

1. CI MSIX production — done (`build_gui.yml`)
2. CI Store upload — done (`publish_msix` in `release.yml` on stable tags)
3. Fix certification failures (capabilities, privacy URL, publisher mismatch, launch crashes)

## Done when

- CI produces versioned MSIX/msixbundle
- Package installs and launches on Windows
- Stable tag releases upload to Partner Center via `publish_msix`
- Listing published (or remediation list owned)

## Do not

- Rewrite the app into a different UI stack for Store access
- Remove the Windows zip release artifact without an explicit ask
- Commit Partner Center credentials or `.pfx` files
