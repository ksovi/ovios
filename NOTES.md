# Review notes for the v6 package set

These recipes were produced offline from the last published Arch recipe for each
package (Arch's own git hosts were unreachable), then re-versioned. **None of them
has been built.** Expect build fixes where upstream changed between the Arch
recipe's version and the v6 version.

## Written from scratch (no Arch snapshot available)
leancrypto, libnghttp3, libngtcp2, libnvme, cockpit-files, perl-http-cookiejar,
python-referencing, python-rpds-py, python-jsonschema-specifications,
qemu-guest-agent (standalone qemu-ga build, systemd unit + udev rule).

## Placeholders (empty packages, real recipe still needed)
gnulib-l10n, gsettings-system-schemas, libmakepkg-dropins.

## Re-split to match the v6 package list
* gcc: libgcc, libstdc++, libgfortran, libgomp, libobjc, libquadmath, libatomic,
  libasan, libhwasan, liblsan, libtsan, libubsan, gcc-libs (meta)
* libblockdev: core + crypto, fs, loop, mdraid, nvme, part, smart, swap plugins
* linux-firmware: per-vendor packages (amdgpu ... realtek, whence, other)
* dbus (+dbus-units), dbus-broker (+dbus-broker-units), python-dbus (was dbus-python)

## Pinned git commits replaced by tags
The Arch recipes pin exact commits. Where the new version's commit is unknown the
recipe now fetches `#tag=...` (brotli, avahi, dconf, glib2, libxml2, polkit, nss,
nspr, grub, binutils, ...). gcc/glibc use the short commit from the v6 version string.

## Likely to need manual work
bash/readline (patch-level scheme), edk2 (bundled openssl/brotli versions are stale),
glibc/gcc/binutils (build flags changed between releases), systemd, python,
perl, linux-api-headers, mkinitcpio family, cloud-init.
