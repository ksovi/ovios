# ovios (v6 branch)

PKGBUILDs for the upstream/Arch-derived packages of OviOS Linux v6, laid out one
directory per `pkgbase` (the Arch convention), Maintainer: Ovi Chis <ovi@ovios.org>.

* The OviOS-specific packages (`ovios-*`, `retadm`, `filesystem`, `lsb-release`,
  `linux`, the storage vendor tools) are **not** here; they live in `ksovi/ovios.v6`.
* Recipes are derived from the Arch Linux package recipes, with `pkgver`/`pkgrel`
  (and `epoch`) set to the v6 package list. Original Arch contributors are kept
  as `# Contributor:` lines.
* Checksums of remote sources whose version changed are `SKIP`; run
  `updpkgsums` in a package directory (with network access) before a release build.
* Several recipes use `arch-meson` (Arch `devtools`); provide an equivalent
  wrapper on the build host or replace it with `meson setup --prefix=/usr ...`.
* See `NOTES.md` for packages that need a human check.
