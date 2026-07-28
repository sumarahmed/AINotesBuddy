export default {
  async fetch(request, env) {
    const response = await env.ASSETS.fetch(request);
    const url = new URL(request.url);

    if (response.status === 404 && !url.pathname.split("/").pop()?.includes(".")) {
      const fallback = new URL("/index.html", request.url);
      return env.ASSETS.fetch(new Request(fallback, request));
    }

    return response;
  },
};
