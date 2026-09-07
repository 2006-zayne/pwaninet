/**
 * semantic-release configuration for PwaniNet
 *
 * Commit message convention (Conventional Commits):
 *   fix: …              → patch bump  (1.0.0 → 1.0.1)
 *   feat: …             → minor bump  (1.0.1 → 1.1.0)
 *   feat!: … or
 *   BREAKING CHANGE: …  → major bump  (1.1.0 → 2.0.0)
 *
 *   chore:, docs:, refactor:, style:, test:, ci:
 *                       → no release (CI skips the APK build)
 */
module.exports = {
  branches: ['main'],

  plugins: [
    // 1. Analyse commits to decide the bump type (or skip if no release)
    [
      '@semantic-release/commit-analyzer',
      {
        preset: 'angular',
        parserOpts: {
          // Lenient pattern: accepts both "fix: msg" and "fix:msg"
          headerPattern: /^(\w+)(?:\(([^)]+)\))?!?:(?:\s*)(.+)$/,
          headerCorrespondence: ['type', 'scope', 'subject'],
        },
        releaseRules: [
          { type: 'feat',     release: 'minor' },
          { type: 'fix',      release: 'patch' },
          { type: 'perf',     release: 'patch' },
          { type: 'revert',   release: 'patch' },
          // Everything else (chore, docs, refactor, style, test, ci) → no release
          { type: 'chore',    release: false },
          { type: 'docs',     release: false },
          { type: 'refactor', release: false },
          { type: 'style',    release: false },
          { type: 'test',     release: false },
          { type: 'ci',       release: false },
        ],
      },
    ],

    // 2. Build human-readable release notes from commit messages
    [
      '@semantic-release/release-notes-generator',
      {
        preset: 'angular',
        parserOpts: {
          headerPattern: /^(\w+)(?:\(([^)]+)\))?!?:(?:\s*)(.+)$/,
          headerCorrespondence: ['type', 'scope', 'subject'],
        },
        writerOpts: {
          // Group commits into sections in the GitHub Release body
          groupBy: 'type',
          commitGroupsSort: 'title',
          commitsSort: ['scope', 'subject'],
        },
      },
    ],

    // 3. Create the GitHub Release (tag + release notes + APK attached by the build job)
    [
      '@semantic-release/github',
      {
        // The APK asset is uploaded by the build job after this step,
        // so we don't list assets here — build job attaches to the same tag.
        successComment: false,  // keep the release page clean
        failComment: false,
      },
    ],
  ],
};
