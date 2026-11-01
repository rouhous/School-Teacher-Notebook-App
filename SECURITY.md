# Application security and reliable deployment

Owner/developer credit: Houssem Lotfi Rouatbi (حسام لطفي الرواتبي).

## Important limitations
The deployed GitHub Pages website is public. HTML, CSS and JavaScript delivered to browsers can be inspected and copied, even if minified or obfuscated. No client-side technique can prevent this completely. Previous public Git commits may remain accessible after future changes.

## Availability-first protection plan
1. Preserve the current known-working deployment and its Git history. Do not obfuscate or rewrite the production HTML in place.
2. Keep the original source in a **private** repository after confirming ownership and collaborator access. A separate public deployment repository can hold compiled/minified assets, but those assets remain inspectable.
3. Build a reproducible staging pipeline with pinned tool versions and dependency integrity checks. Minify and optionally obfuscate only application-owned JavaScript, never vendor bundles without license review. Preserve required global function names, inline event handlers, dynamic imports, and service worker scope.
4. Verify login, supervisor approval, teacher schedule, rosters, attendance, grade saving, offline behavior, and restore on Android/iOS/desktop before switching production. Retain a rollback artifact and verify deployment health.
5. Keep credentials and privileged operations on the server; use Supabase row-level security and role policies, and audit any publicly exposed keys. Public anon keys are not secrets; service-role keys must never be embedded in browser code.
6. Restrict repository write access, enable 2FA, branch protection, and secret scanning where supported. Review third-party asset licenses and contributor rights.

## Current state
This file and the LICENSE notice are documentation-only protections. They do not alter runtime behavior or establish that source-code obfuscation, private hosting, security hardening, or an end-to-end regression test has been completed.
