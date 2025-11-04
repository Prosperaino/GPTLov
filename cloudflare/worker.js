const ROUTES = [
  {
    prefix: "/gptlov",
    envKey: "GPTLOV_ORIGIN",
    stripPrefix: true,
  },
  // Add more applications here, for example:
  // {
  //   prefix: "/another-app",
  //   envKey: "ANOTHER_APP_ORIGIN",
  //   stripPrefix: true,
  // },
];

const LABS_HOME_HTML = `<!DOCTYPE html>
<html lang="no">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Prosper AI Labs</title>
    <style>
      :root {
        color-scheme: light dark;
        --accent: #171717;
        --muted: rgba(23, 23, 23, 0.6);
        --border: rgba(23, 23, 23, 0.12);
      }
      * {
        box-sizing: border-box;
      }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
        display: grid;
        place-items: center;
        background: #f7f7f7;
        color: var(--accent);
      }
      main {
        max-width: 420px;
        padding: 4rem 2.8rem;
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border);
        border-radius: 20px;
        text-align: center;
        box-shadow: 0 20px 40px rgba(17, 24, 39, 0.08);
      }
      .wordmark {
        display: inline-flex;
        align-items: baseline;
        gap: 0.35rem;
        font-size: 2.05rem;
        font-weight: 600;
        letter-spacing: -0.03em;
      }
      .wordmark span:last-child {
        font-size: 1.6rem;
        font-weight: 500;
        color: var(--muted);
      }
      p {
        margin: 1.6rem 0 0;
        font-size: 1.04rem;
        line-height: 1.6;
        color: var(--muted);
      }
      a {
        color: inherit;
        text-decoration: none;
        border-bottom: 1px solid rgba(23, 23, 23, 0.25);
        padding-bottom: 2px;
      }
      a:hover {
        border-bottom-color: var(--accent);
      }
      @media (max-width: 540px) {
        main {
          margin: 3rem 1.5rem;
          padding: 3rem 2rem;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <div class="wordmark"><span>Prosper AI</span><span>Labs</span></div>
      <p>Eksperimenter og prototyper.</p>
      <p><a href="https://prosper-ai.no" rel="noopener">Tilbake til prosper-ai.no</a></p>
    </main>
  </body>
</html>`;

function normalisePrefix(prefix) {
  return prefix.endsWith("/") ? prefix : `${prefix}/`;
}

function matchRoute(pathname) {
  for (const route of ROUTES) {
    const normalisedPrefix = normalisePrefix(route.prefix);
    const trimmedPrefix = normalisedPrefix.slice(0, -1);

    if (pathname === trimmedPrefix || pathname === normalisedPrefix) {
      return { route, strippedPath: "/" };
    }

    if (pathname.startsWith(normalisedPrefix)) {
      const remainder = pathname.slice(normalisedPrefix.length).replace(/^\/+/, "");
      const strippedPath = remainder ? `/${remainder}` : "/";
      return { route, strippedPath };
    }
  }
  return null;
}

function buildTargetUrl(origin, path, search) {
  const base = origin.endsWith("/") ? origin : `${origin}/`;
  const target = new URL(base);
  target.pathname = path;
  target.search = search;
  return target.toString();
}

function rewriteHtml(content, prefix) {
  const normalisedPrefix = normalisePrefix(prefix);
  return content
    .replace(/(href|src|action)="\/(?!\/)/g, `$1="${normalisedPrefix}`)
    .replace(/fetch\(\s*["']\/(?!\/)/g, `fetch("${normalisedPrefix}`)
    .replace(/axios\.(get|post|put|patch|delete)\(\s*["']\/(?!\/)/g, `axios.$1("${normalisedPrefix}`);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/" || url.pathname === "") {
      return new Response(LABS_HOME_HTML, {
        status: 200,
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    for (const route of ROUTES) {
      if (
        url.pathname === route.prefix &&
        route.prefix !== "/" &&
        !url.pathname.endsWith("/")
      ) {
        const redirectUrl = new URL(url);
        redirectUrl.pathname = `${route.prefix}/`;
        return Response.redirect(redirectUrl.toString(), 301);
      }
    }

    const match = matchRoute(url.pathname);

    if (!match) {
      return new Response("Not found", { status: 404 });
    }

    const origin = env[match.route.envKey];
    if (!origin) {
      return new Response(
        `Missing origin configuration for ${match.route.envKey}`,
        { status: 502 },
      );
    }

    const targetPath = match.route.stripPrefix ? match.strippedPath : url.pathname;
    const targetUrl = buildTargetUrl(origin, targetPath, url.search);

    const init = {
      method: request.method,
      headers: request.headers,
      redirect: "manual",
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = request.body;
    }

    const upstreamResponse = await fetch(new Request(targetUrl, init));

    if (match.route.stripPrefix) {
      const contentType = upstreamResponse.headers.get("content-type") || "";
      if (contentType.includes("text/html")) {
        const html = await upstreamResponse.text();
        const rewritten = rewriteHtml(html, match.route.prefix);
        const headers = new Headers(upstreamResponse.headers);
        headers.delete("content-length");
        return new Response(rewritten, {
          status: upstreamResponse.status,
          statusText: upstreamResponse.statusText,
          headers,
        });
      }
    }

    return upstreamResponse;
  },
};
