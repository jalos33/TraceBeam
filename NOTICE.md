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

## MIT / BSD packages

All other dependencies above are permissively licensed (MIT / BSD-3-Clause)
and require only that their copyright notice and license text be preserved
somewhere in the distribution, which their own `dist-info`/`METADATA`
already does when installed via `pip`, and which this file does explicitly
for the executable distributions.
