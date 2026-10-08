# License and upstream attribution

The root MIT license covers original project helpers and documentation.
Upstream components and patches to their files retain their upstream terms.

- **Omarchy ARM desktop/configuration:** BlackFireAlex/omarchy-android, MIT;
  its notice is preserved in `LICENSES/omarchy-android-MIT.txt`.
- **amonet patches:** R0rt1z2/amonet, per-file MIT/GPL v2 terms; the notices
  are preserved in `LICENSES/amonet-MIT.txt` and `LICENSES/amonet-GPL-2.0.txt`.
- **wvkbd feedback patch:** jjsullivan5196/wvkbd, GPL v3 with the MIT components
  listed in COPYING. Notices are preserved under `LICENSES/wvkbd-*`.
- **Other downloaded software:** the postmarketOS giza kernel, Arch Linux ARM
  packages, eudev, desktop bundles and mtk-su retain their upstream licenses.
  Downloaded binaries and firmware are excluded from this Git repository.

`sources.lock.json` records source URLs and exact revisions. The repository
contains reviewed text patches, not an unlock-tool binary distribution.
The keyboard is built separately from the pinned upstream source plus
`patches/wvkbd-immediate-feedback.patch`; no keyboard binary is shipped here.
Firmware, raw logs, partition backups and device identifiers remain local.
