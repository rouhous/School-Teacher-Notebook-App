# School Teacher Notebook Android Widget (pilot)
Free Android debug APK built by GitHub Actions. This is a pilot, not a production release.
Open the hosted teacher notebook inside the app, sign in, wait for the approved schedule, then tap **تحديث الويدجت**.
The widget caches only the approved schedule/cover snapshot on the device. Never store tokens or passwords in widget preferences.
Caution: Google sign-in may reject embedded WebView; browser-based authentication and secure session handoff must be completed before production rollout. Do not distribute broadly until tested.
Build: Actions > Build Android Teacher Widget > Run workflow. Download the artifact from the completed run.
