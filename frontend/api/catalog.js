const catalog = {
  profile: "https://www.rfc-editor.org/info/rfc9727",
  linkset: [
    {
      anchor: "https://prep-academy.onrender.com/api",
      "service-desc": [
        {
          href: "https://prep-academy.onrender.com/openapi.json",
          type: "application/vnd.oai.openapi+json;version=3.0",
        },
      ],
      "service-doc": [
        {
          href: "https://github.com/metwally99594/prep-academy/tree/main/docs",
          type: "text/html",
        },
      ],
      status: [
        {
          href: "https://prep-academy.onrender.com/api/health",
          type: "application/json",
        },
      ],
    },
  ],
};

export default function handler(request, response) {
  if (request.method === "HEAD") {
    response
      .status(200)
      .setHeader(
        "Link",
        '<https://prepacademy-med.com/.well-known/api-catalog>; rel="api-catalog"'
      )
      .end();
    return;
  }

  response
    .status(200)
    .setHeader("Content-Type", "application/linkset+json; charset=utf-8")
    .setHeader("Cache-Control", "public, max-age=300")
    .send(JSON.stringify(catalog));
}
