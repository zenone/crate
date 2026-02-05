# Variant: Next.js (default web stack)

This variant is meant to be the "default" 2026 web app choice.

Recommended stack:
- Next.js 15+ (App Router)
- TypeScript
- Postgres + Prisma/Drizzle
- Auth.js (or Clerk)
- Tailwind + shadcn
- Vitest + Playwright

Bootstrap suggestion:
```bash
npx create-next-app@latest . --ts --eslint --tailwind
```

Then wire `Makefile` targets and optionally copy CI scaffold.
