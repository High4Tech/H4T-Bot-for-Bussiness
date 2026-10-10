# Local typography

The current shadcn/ui interface uses bundled Geist. Earlier PP Neue Montreal and Helvetica Neue files are retained locally as reference assets and are not loaded by the app.

The six fonts supplied by the user are installed locally under `private/`, which is ignored by Git. No redistribution permission was present in the ZIPs; font binaries are not published with the source. A fresh checkout uses Helvetica/Arial fallbacks until its licensed copies are imported with `scripts/import-fonts.ps1`.
