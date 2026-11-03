# Community hardware reports

There is no brand/model allowlist. A missing row is an invitation to try the
software, not a declaration that your hardware is unsupported.

| Laptop / touchpad | Input identity | Environment | Result / coverage |
| --- | --- | --- | --- |
| MacBook Pro 2017 / Apple SPI Touchpad | `001c:06cb:0557` | Ubuntu 26.04, GNOME 50, Wayland | Five positions tracked (11 slots); pinch candidates and live app-grid open/close confirmed. Package installation confirmed. 0.5.0 generic discovery/reader lifecycle rechecked. Balanced sensitivity in the local 0.6.0 trial confirmed comfortable by the user; Original and Relaxed remain available. |

**Everything else:** not yet tested by this project. It may work without changes.
Please send a documentation PR with your results, or a code PR with any improvements
needed to make it work. See [CONTRIBUTING](../CONTRIBUTING.md).

A report confirms only the checks it lists, not every feature, firmware revision
or future GNOME version. In particular, successful device discovery alone is not
a successful gesture test.
