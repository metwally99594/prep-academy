const markdown = `# Prep Academy Elite

Prep Academy is an AI-assisted medical exam preparation platform for learners in Austria, Germany, and Switzerland.

## Public resources

- API catalog: https://prepacademy-med.com/.well-known/api-catalog
- API health: https://prep-academy.onrender.com/api/health
- OpenAPI: https://prep-academy.onrender.com/openapi.json
- Guest practice: https://prepacademy-med.com/guest-quiz
- Registration: https://prepacademy-med.com/register
- Authentication instructions: https://prepacademy-med.com/auth.md

## Main capabilities

- Public guest medical questions
- Specialty and exam-location discovery
- Authenticated quizzes, review, statistics, and community features
- Optional AI tutor, analyzer, notebook, and DICOM modules when enabled
`;

export default function handler(_req, res) {
  res.statusCode = 200;
  res.setHeader("Content-Type", "text/markdown; charset=utf-8");
  res.setHeader("X-Markdown-Tokens", String(Math.ceil(markdown.length / 4)));
  res.setHeader("Cache-Control", "public, max-age=300");
  res.end(markdown);
}
