/**
 * Static export, per C7.3 and C11.3.
 *
 * `output: "export"` is load-bearing rather than a deployment convenience. C11.3 asks for a
 * "server-rendered featured comparison" on arrival, and with a static export that becomes a
 * **build-time** data dependency instead of a runtime one — the featured comparison is in
 * the HTML before the first byte reaches a browser, so B4 #8's cached-path budget (p90 < 5s)
 * is met by there being nothing to wait for.
 *
 * It also means the frontend has no server of its own. ADR-003 deleted the deployment; the
 * backend mounts this export as static files, and in fixtures mode it opens from the
 * filesystem with nothing running at all.
 */
const nextConfig = {
  output: "export",
  // A static export cannot use the image optimiser, which needs a server.
  images: { unoptimized: true },
  // Trailing slashes keep `out/` openable directly from the filesystem — the demo's
  // fallback path when the backend is not running (ADR-003: one laptop, several ways to
  // fail).
  trailingSlash: true,
  reactStrictMode: true,
};

export default nextConfig;
