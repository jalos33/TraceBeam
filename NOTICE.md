# Third-Party Notices

TraceBeam is MIT-licensed (see `LICENSE`). It depends on the open-source
packages below. Running from source, none of this requires anything beyond
normal `pip install`. The prebuilt executables (built via PyInstaller)
bundle these packages' code directly into the binary, which is why this
file exists — to be explicit about what's inside and under what terms.

| Package | Version floor | License | Modified? |
|---------|---------------|---------|-----------|
| fastapi | ≥0.136.1 | MIT | No |
| starlette | ≥1.3.1 | BSD-3-Clause | No |
| uvicorn | ≥0.34.0 | BSD-3-Clause | No |
| sqlalchemy | ≥2.0.0 | MIT | No |
| apscheduler | ≥3.10.0 | MIT | No |
| pyyaml | ≥6.0 | MIT | No |
| icmplib | ≥3.0.4 | **LGPL-3.0** | No |
| platformdirs | ≥4.4.0 | MIT | No |
| Chart.js (vendored, `tracebeam/static/js/vendor/chart.umd.min.js`) | 4.4.7 | MIT | No |

## Transitive dependencies bundled in the executables

The prebuilt executables bundle not just the direct dependencies above but
their full dependency closure. Every additional package pulled in is
permissively licensed. The complete bundled runtime closure and its licenses:

| Package | License |
|---------|---------|
| annotated-doc | MIT |
| annotated-types | MIT |
| anyio | MIT |
| click | BSD-3-Clause |
| h11 | MIT |
| httptools | MIT |
| idna | BSD-3-Clause |
| packaging | Apache-2.0 OR BSD-2-Clause |
| pydantic | MIT |
| pydantic-core | MIT |
| python-dotenv | BSD-3-Clause |
| sortedcontainers | Apache-2.0 |
| tzlocal | MIT |
| typing-extensions | PSF-2.0 |
| uvloop | Apache-2.0 / MIT (dual) |
| watchfiles | MIT |
| websockets | BSD-3-Clause |

**The only copyleft license anywhere in the bundled binary is `icmplib`'s
LGPL-3.0** (handled below). Every other bundled package — direct or transitive
— is permissive (MIT / BSD / Apache-2.0 / PSF). There is no GPL or other
strong-copyleft code in the distribution.

> Regenerate this list after a dependency bump with:
> `pip-licenses --format=markdown --with-urls` (or emit an SBOM with the
> already-vendored `cyclonedx-bom`). Versions drift; the license mix is what
> matters here.

## LGPL-3.0 note (icmplib)

`icmplib` is licensed under the GNU Lesser General Public License v3.0. Its
full license text ships with the package itself (from PyPI) and is
reproduced in this project's dependency tree — see
[icmplib's repository](https://github.com/ValentinBELYN/icmplib) for its
canonical source.

TraceBeam uses `icmplib` **unmodified**, calling only its public API
(`ping()`, `traceroute()`) from `tracebeam/monitor.py`. Under LGPL-3.0 §4,
an unmodified Library used through its published interface by an
Application (this is exactly that case) permits combining/bundling; the
practical obligation is that the Library's Minimal Corresponding Source
remain available. Since `icmplib` is pure Python, unmodified, and
published in full at `https://github.com/ValentinBELYN/icmplib` and
`https://pypi.org/project/icmplib/`, that condition is satisfied by this
notice pointing there.

If you fork this project and modify `icmplib` itself before bundling it,
different LGPL obligations apply (you'd need to distribute the modified
source or object files enabling relinking) — this notice only covers the
unmodified-use case that TraceBeam actually does.

### Corporate / internal-use note (icmplib LGPL-3.0)

For organizations evaluating TraceBeam:

- **Internal use triggers no LGPL distribution obligations.** The LGPL's
  obligations attach to *distribution*, not to running the software. A company
  that downloads and runs TraceBeam (or builds it from source) on its own
  machines owes nothing under the LGPL.
- **If your organization redistributes the bundled executable** — to a separate
  legal entity, a contractor, a subsidiary, or externally — the LGPL-3.0
  relinking obligation for `icmplib` applies. Because TraceBeam uses `icmplib`
  **unmodified, through its public API**, and `icmplib` is **pure Python** and
  published in full at <https://github.com/ValentinBELYN/icmplib>, that
  obligation is satisfied by (a) preserving this notice and (b) the recipient's
  ability to replace the bundled `icmplib` with their own copy. No proprietary
  or copyleft source of TraceBeam's own needs to be disclosed.
- **No other copyleft is present.** Every other bundled dependency (direct or
  transitive) is permissive (MIT / BSD / Apache-2.0 / PSF). See the tables above.

## Permissive packages (MIT / BSD / Apache-2.0 / PSF)

Every other dependency — direct and transitive — is permissively licensed
(MIT / BSD-3-Clause / Apache-2.0 / PSF-2.0). These require only that their
copyright notice and license text be preserved somewhere in the distribution,
which their own `dist-info`/`METADATA` already does when installed via `pip`,
and which this file does explicitly for the executable distributions. None of
them impose copyleft or source-disclosure obligations.
