# CLAUDE.md - AI Assistant Guide for Ably Specification Repository

This document provides comprehensive guidance for AI assistants working on the Ably Features Specification repository.

## Repository Overview

This is the **Ably Features Specification** repository - the authoritative source for defining the interfaces, behaviors, and implementation details for Ably SDKs (client libraries) across all platforms and languages. It serves as the reference guide for SDK developers implementing support for the Ably realtime platform.

**Key Facts:**
- **Primary Language:** Textile markup (RedCloth), with some Markdown
- **Build Tools:** Ruby scripts, Node.js for CSS processing
- **Current Specification Version:** 5.0.0 (defined in `meta.yaml`)
- **Current Protocol Version:** 5 (defined in `meta.yaml`)
- **CI/CD:** GitHub Actions (check.yaml, assemble.yml)
- **Output:** Static HTML microsite deployed to AWS S3

## Repository Structure

```
specification/
├── textile/                    # Core specification documents
│   ├── features.textile        # Main SDK spec (REST/Realtime, 3076 lines)
│   ├── chat-features.textile   # Ably Chat product spec (1708 lines)
│   ├── objects-features.textile # Objects (state sync) spec (620 lines)
│   ├── protocol.textile        # Wire protocol definition
│   ├── websocket.textile       # WebSocket transport spec
│   ├── comet.textile          # Comet (long-polling) transport spec
│   ├── encryption.textile      # End-to-end encryption spec
│   ├── test-api.textile       # Sandbox Test API spec
│   ├── index.textile          # Client Library Development Guide
│   ├── versioning.textile     # Versioning guidelines
│   ├── feature-prioritisation.textile # Feature prioritization guidance
│   ├── api-docstrings.md      # Language-agnostic API documentation
│   └── notes-in-relation-to-move-from-ably-docs.md # Historical notes
├── scripts/                    # Build and validation scripts (Ruby)
│   ├── build                  # Main build script (textile → HTML)
│   └── find-duplicate-spec-items # Spec ID validation script
├── templates/                  # HTML templates and styling
│   ├── docs-textile.html.hbs  # Handlebars template for HTML pages
│   └── main.css               # Tailwind CSS base styles
├── .github/workflows/         # CI/CD automation
│   ├── check.yaml            # Linting and validation
│   └── assemble.yml          # Build and deploy to S3
├── output/                    # Generated HTML (gitignored, build artifact)
├── meta.yaml                 # Version numbers (spec + protocol)
├── package.json              # Node.js build scripts and dependencies
├── .tool-versions            # asdf version specifications
├── .editorconfig             # Code formatting rules
├── tailwind.config.js        # Tailwind CSS configuration
├── README.md                 # Repository documentation
└── CONTRIBUTING.md           # Contribution guidelines
```

## Three Independent Version Numbers

This repository tracks **three separate versions** - understanding these is critical:

### 1. Specification Version (SemVer in `meta.yaml`)
- **Current:** 5.0.0
- **Format:** Semantic Versioning (X.Y.Z)
- **Scope:** The specification content itself (files in `textile/`)
- **Bumped when:**
  - **Major:** Breaking SDK API changes, breaking behavior changes
  - **Minor:** New features, backwards-compatible enhancements
  - **Patch:** Typos, formatting, clarity improvements (no semantic changes)
- **Release Process:** Bumped in release branches, tagged as `vX.Y.Z`, `vX.Y`, `vX`

### 2. Protocol Version (Integer in `meta.yaml`)
- **Current:** 5
- **Format:** Integer (was decimal before v2)
- **Scope:** Wire protocol used between SDKs and Ably service
- **Bumped when:**
  - Wire protocol API changes
  - Service behavior changes that SDKs must respond to
  - SDK behavior changes that service must respond to
- **Important:** NOT bumped in release process - bumped as part of feature PRs

### 3. Build Version (SemVer in `package.json`)
- **Current:** 1.0.0 (static, nominal importance)
- **Format:** Semantic Versioning
- **Scope:** Build tooling (scripts, templates, CSS)
- **Note:** Not currently used for releases; may change if tools exported as npm package

**⚠️ When making changes:**
- Most PRs will NOT change any version numbers
- Specification version is only bumped during the formal release process
- Protocol version is bumped in feature PRs that affect wire protocol
- Build version is rarely changed (tooling is internal-only)

## Specification Point (Spec Point) System

### What are Spec Points?

Spec points are numbered/lettered identifiers (e.g., `RTL18`, `CSV1a`, `CHA-GP1`) that uniquely identify requirements in the specification. They enable:
- Cross-referencing between specification sections
- SDK compliance tracking (which features are implemented)
- Test coverage alignment
- Precise communication about requirements

### Spec Point ID Format

```
XXX1        # Top-level point
XXX1a       # First subclause of XXX1
XXX1b       # Second subclause of XXX1
XXX1a1      # First sub-subclause of XXX1a
XXX1a2      # Second sub-subclause of XXX1a
```

**Examples from the spec:**
- `RTL18` - Realtime Libraries point 18
- `CSV1a` - Client Server Versioning point 1, subclause a
- `CHA-GP1` - Chat General Presence point 1

### Critical Rules for Spec Points

#### 1. Spec Points are IMMUTABLE
- **Never delete** a spec point completely from the document
- **Never reuse** a deleted spec point ID
- **Never mutate** existing spec points (except for non-semantic fixes like typos)

#### 2. Adding New Spec Points
- Choose an ID **greater than all existing IDs** in that section
- Even if there are gaps (e.g., XXX1, XXX2, XXX5 exist), use XXX6 for new point
- Order spec points logically for coherence, not strictly by ID number
- Parent clauses should be informational headers; put behavior in subclauses
- Avoid conditionals within a single spec point; split into separate subclauses

#### 3. Removing Spec Points
When a spec point is no longer valid:

```textile
h6(#XXX1). XXX1

This clause has been deleted. It was valid up to and including specification version @5.0@.
```

**Variations allowed:**
```textile
This clause has been deleted (redundant to "RTN19a":#RTN19a). It was valid up to and including specification version @1.2@.
```

If a spec point has subclauses, they must also be marked as removed/replaced.

#### 4. Replacing Spec Points
When a spec point is superseded by a new one:

```textile
h6(#XXX1). XXX1

This clause has been replaced by "@XXX7@":#XXX7. It was valid up to and including specification version @5.0@.
```

**Multiple replacements:**
```textile
This clause has been replaced by "@RTN16g@":#RTN16g and "@RTN16m@":#RTN16m. It was valid up to and including specification version @1.2@.
```

#### 5. Deprecating Spec Points
Prefix the spec point text with "(deprecated)":

```textile
h6(#XXX1). XXX1

(deprecated) This feature should no longer be used and will be removed in a future release.
```

### Spec Point Syntax in Textile

**Creating a spec point anchor:**
```textile
h6(#RTL18). RTL18
```

**Referencing a spec point:**
```textile
See "@RTL18@":#RTL18 for details.
```

**Inline spec point notation:**
```textile
* @(RTL18)@ The client must reconnect automatically
```

The build script automatically converts these to clickable HTML anchors.

## Development Workflow

### Local Setup

**Prerequisites:**
```bash
# Install required tools (versions from .tool-versions)
# Ruby 3.4.7
# Node.js 22.19.0

# Using asdf (recommended):
asdf install
```

**Install dependencies:**
```bash
npm install
```

### Building Locally

```bash
# Clean and rebuild everything
npm run build

# Or step by step:
npm run clean              # Remove output/
./scripts/build            # Generate HTML from textile
npm run build:tailwind     # Process CSS
```

**Preview the output:**
```bash
open output/index.html     # macOS
# Or manually open output/index.html in your browser
```

**Note:** Uses `file://` protocol, so navigating requires two clicks (folder → index.html)

### Validation

```bash
# Check for duplicate spec IDs
npm run lint
```

This runs `./scripts/find-duplicate-spec-items` which scans for duplicate spec point IDs across all textile files.

### Making Changes

**Typical workflow:**
1. Edit `.textile` or `.md` files in `textile/` directory
2. Run `npm run build` to regenerate HTML
3. Open `output/index.html` to preview changes
4. Run `npm run lint` to validate
5. Commit changes (DO NOT commit `output/` directory)
6. Push to branch and create PR

**When editing spec files:**
- Follow spec point lifecycle rules (see above)
- Use proper Textile markup syntax
- Maintain consistent formatting per `.editorconfig`
- Update `textile/api-docstrings.md` in same PR if adding new API fields
- Never commit the `output/` directory (it's gitignored)

## Textile Markup Reference

**Headings:**
```textile
h1. Heading 1
h2. Heading 2
h3. Heading 3
h4. Heading 4
h5. Heading 5
h6. Heading 6
```

**Spec point anchors:**
```textile
h6(#RTL18). RTL18
```

**Links:**
```textile
"Link text":https://example.com
"Internal link":#anchor-id
"@Spec point@":#RTL18
```

**Lists:**
```textile
* Bullet point
* Another bullet

# Numbered list
# Second item
```

**Code:**
```textile
@inline code@

bc. code block
multiple lines
```

**Emphasis:**
```textile
*bold*
_italic_
```

**Version placeholders:**
```textile
{{ SPECIFICATION_VERSION }}   # Replaced with value from meta.yaml
{{ PROTOCOL_VERSION }}         # Replaced with value from meta.yaml
```

## File-Specific Guidelines

### textile/features.textile
- **Size:** 330KB, 3076 lines - the largest and most important spec
- **Contains:** REST client, Realtime client, channels, messages, presence, auth
- **Spec prefixes:** RTL (Realtime), RSC (REST Client), RSA (REST Auth), etc.
- **When editing:** Be extremely careful with spec point IDs; this file has the most

### textile/chat-features.textile
- **Size:** 111KB, 1708 lines
- **Contains:** Ably Chat product specification
- **Spec prefixes:** CHA-* (e.g., CHA-GP1, CHA-M1)
- **Status:** Newer specification for chat features

### textile/objects-features.textile
- **Size:** 72KB, 620 lines
- **Contains:** Ably Objects (distributed state synchronization)
- **Spec prefixes:** OB-* patterns

### textile/api-docstrings.md
- **Purpose:** Language-agnostic API documentation for SDK developers
- **Format:** Markdown tables
- **Important:** Update this in same PR when adding new API fields
- **Conventions:**
  - Use verbs with 's' for methods (retrieves, registers, publishes)
  - Hyphenate "key-value pairs"
  - Link format: `` [`ClassName`]{@link ClassName#property} ``
  - Capitalize class/object names, lowercase methods/parameters
  - Include DEPRECATED notice for deprecated items
  - List default values and min/max constraints

### scripts/build
- **Language:** Ruby (self-contained dependencies via Bundler inline)
- **Purpose:** Main build script
- **What it does:**
  1. Reads `meta.yaml` for version numbers
  2. Parses all `.textile` and `.md` files from `textile/`
  3. Processes RedCloth markup with custom extensions
  4. Replaces version placeholders
  5. Renders HTML using Handlebars template
  6. Creates directory structure in `output/`
- **Dependencies:** RedCloth (~4.3.2), ruby-handlebars (~0.4.1), Kramdown (~2.4.0)
- **When editing:** Ruby experience required; affects entire build pipeline

### scripts/find-duplicate-spec-items
- **Language:** Ruby
- **Purpose:** Validates no duplicate spec point IDs
- **What it does:**
  1. Scans features.textile, chat-features.textile, objects-features.textile
  2. Extracts all spec IDs using regex: `@\(([A-Z0-9-]+[a-z0-9]*)\)@`
  3. Reports duplicates with file locations
  4. Exits with code 1 if duplicates found (fails CI)
- **Runs:** During `npm run lint` and in CI check workflow

### templates/docs-textile.html.hbs
- **Format:** Handlebars template
- **Purpose:** HTML page structure for all spec pages
- **Variables:**
  - `bodyContent` - Rendered HTML from textile
  - `title` - Page title
  - `file_names` - Array of all spec files for navigation
  - `root_path` - Relative path to root
  - `copyright` - Copyright notice
  - `build_context_*` - CI/CD context (SHA, URL, title)
- **When editing:** Changes affect all generated pages

### templates/main.css
- **Format:** Tailwind CSS with `@layer` directives
- **Purpose:** Base styling for specification pages
- **Processed by:** `tailwindcss` CLI during build
- **Output:** `output/tailwind.css` (minified)
- **When editing:** Use Tailwind utilities; rebuild to see changes

## CI/CD Pipeline

### .github/workflows/check.yaml
**Trigger:** Pull requests, pushes to main
**Steps:**
1. Checkout code
2. Setup Ruby 3.4.7 and Node.js 22.19.0
3. Install dependencies: `npm ci`
4. Run linting: `npm run lint` (validates duplicate spec IDs)

**Status badge:** Displayed in README.md

### .github/workflows/assemble.yml
**Trigger:** Pull requests, pushes to main, tagged releases (`v*`)
**Steps:**
1. Checkout code
2. Get build context (SHA, PR title/URL) via `ably/github-event-context-action`
3. Setup Ruby and Node.js
4. Run full build: `npm run build`
5. Configure AWS credentials
6. Upload to S3 via `ably/sdk-upload-action`

**Build context variables injected:**
- `ABLY_BUILD_CONTEXT_SHA` - Git commit SHA
- `ABLY_BUILD_CONTEXT_URL` - PR URL or commit URL
- `ABLY_BUILD_CONTEXT_TITLE` - PR title or branch name

**Output:** Static HTML site at https://sdk.ably.com/builds/ably/specification/

## Git and Branch Workflow

### Branch Naming
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- Documentation: `docs/description`
- Claude AI branches: `claude/claude-md-*` (from session context)

### Commit Messages
- Follow conventional commits style when possible
- Be descriptive about what changed and why
- Reference issue numbers if applicable

### Pull Request Process
1. Create feature branch from `main`
2. Make changes following spec point rules
3. Run `npm run build` and `npm run lint` locally
4. Commit and push to branch
5. Create PR with clear description
6. CI runs check and assemble workflows
7. Review by SDK team members
8. Merge to main after approval

### Release Process
**Follow:** https://github.com/ably/engineering/blob/main/sdk/releases.md#release-process

**Key points:**
- Create release branch
- Bump specification version in `meta.yaml` (NOT protocol or build version)
- Update changelog if exists
- Create PR for release branch
- After merge, create Git tags:
  - `vX.Y.Z` - Full version tag (immutable)
  - `vX.Y` - Minor version tag (moves to latest patch)
  - `vX` - Major version tag (moves to latest minor)

## Important Conventions for AI Assistants

### DO:
- ✅ Read the relevant textile files completely before suggesting changes
- ✅ Validate spec point IDs before adding new ones
- ✅ Follow the spec point lifecycle rules strictly
- ✅ Run `npm run build` and `npm run lint` before committing
- ✅ Check for duplicate spec IDs manually if adding many new points
- ✅ Update `api-docstrings.md` when adding new API surface area
- ✅ Use proper Textile markup syntax
- ✅ Maintain existing formatting and style conventions
- ✅ Reference existing spec points by ID when explaining relationships
- ✅ Test that generated HTML renders correctly
- ✅ Preserve git history by following commit message conventions

### DON'T:
- ❌ Never delete spec points completely - mark as removed instead
- ❌ Never reuse deleted spec point IDs
- ❌ Never mutate existing spec points (except non-semantic fixes)
- ❌ Never commit the `output/` directory
- ❌ Never change version numbers without understanding the process
- ❌ Never add spec points with IDs lower than existing ones in that section
- ❌ Never use placeholders or guess version numbers
- ❌ Never skip running validation (`npm run lint`) before committing
- ❌ Never break Textile markup syntax
- ❌ Never introduce duplicate spec point IDs

### When Adding Features:
1. Identify the appropriate textile file (features.textile, chat-features.textile, etc.)
2. Find the relevant section and note the highest existing spec ID
3. Create new spec point with next available ID
4. Structure with parent clause as header, behavior in subclauses
5. Avoid conditionals; split into multiple spec points if needed
6. Add corresponding docstrings to `api-docstrings.md`
7. Build and validate locally
8. Ensure no duplicate IDs introduced

### When Modifying Existing Spec:
1. Identify the spec point ID that needs changing
2. Determine if this is:
   - Non-semantic fix (typo, clarity) → Edit in place
   - Semantic change → Mark as replaced, create new spec point
   - Removal → Mark as deleted with version number
   - Deprecation → Add "(deprecated)" prefix
3. If replacing, create new spec point with higher ID
4. Update cross-references to point to new spec ID if replaced
5. Run validation to ensure no duplicates

### When Reviewing Changes:
- Check that new spec IDs are higher than existing ones
- Verify Textile markup is correct
- Ensure removed/replaced points retain their ID and location
- Confirm version placeholders are used correctly
- Validate that changes align with specification version policy
- Test that HTML renders correctly

## Common Tasks

### Add a New Feature Specification
```bash
# 1. Edit the appropriate textile file
vim textile/features.textile

# 2. Find highest spec ID in section (e.g., RTL18)
# 3. Add new spec point with ID RTL19
# 4. Build and validate
npm run build
npm run lint

# 5. Preview
open output/features/index.html

# 6. Update docstrings if API changes
vim textile/api-docstrings.md

# 7. Commit and push
git add textile/features.textile textile/api-docstrings.md
git commit -m "Add RTL19: New feature specification"
git push
```

### Remove/Replace a Spec Point
```bash
# 1. Edit the textile file
vim textile/features.textile

# 2. Find the spec point (e.g., RTL15)
# 3. Replace content with removal/replacement notice:
#    "This clause has been deleted. It was valid up to and including specification version @5.0@."
# 4. If replacing, create new spec point with higher ID
# 5. Build, validate, commit
npm run build && npm run lint
git add textile/features.textile
git commit -m "Remove RTL15, replace with RTL20"
git push
```

### Update Protocol Version
```bash
# Only do this if wire protocol changes!
# 1. Edit meta.yaml
vim meta.yaml
# Change: protocol: 5 -> protocol: 6

# 2. Document in textile files what changed
vim textile/protocol.textile

# 3. Build and commit
npm run build
git add meta.yaml textile/protocol.textile
git commit -m "Bump protocol version to 6 for [reason]"
git push
```

### Fix a Build Error
```bash
# 1. Check the error message from CI or local build
npm run build 2>&1 | tee build.log

# 2. Common issues:
#    - Duplicate spec IDs: Run npm run lint to find them
#    - Textile syntax errors: Check RedCloth markup
#    - Missing files: Ensure all referenced files exist

# 3. Fix and rebuild
npm run build

# 4. Validate
npm run lint
```

## Troubleshooting

### "Duplicate spec item IDs found"
- Run `./scripts/find-duplicate-spec-items` to see which IDs are duplicated
- Check if recent PRs merged concurrently introduced same IDs
- Renumber one of the duplicate IDs to next available number
- Rebuild and validate

### Build fails with RedCloth error
- Check Textile markup syntax in the affected file
- Ensure all heading levels are correct (h1-h6)
- Verify anchor syntax: `h6(#ID). ID`
- Check for unclosed markup tags

### HTML not rendering correctly
- Verify Textile markup is valid
- Check that version placeholders are correct: `{{ SPECIFICATION_VERSION }}`
- Ensure CSS is being generated: `ls output/tailwind.css`
- Rebuild from scratch: `npm run clean && npm run build`

### Changes not appearing in output
- Ensure you rebuilt: `npm run build`
- Clear browser cache and refresh
- Check that you edited the source file, not the output file
- Verify file saved before building

## External Resources

- **Main Documentation:** https://ably.com/documentation
- **SDK Repositories:** https://github.com/ably (various language SDKs)
- **Engineering Docs:** https://github.com/ably/engineering
- **Specification Builds:** https://sdk.ably.com/builds/ably/specification/
- **RedCloth Documentation:** https://redcloth.github.io/redcloth/
- **Handlebars Documentation:** https://handlebarsjs.com/

## Quick Reference

### File Extensions
- `.textile` - Textile markup specification files (RedCloth)
- `.md` - Markdown documentation files
- `.html.hbs` - Handlebars HTML templates
- `.css` - Tailwind CSS styling
- `.yaml` / `.yml` - Configuration files
- `.js` - JavaScript configuration (minimal)

### Key Commands
```bash
npm install              # Install dependencies
npm run build            # Full build (clean + generate + CSS)
npm run clean            # Remove output directory
npm run lint             # Validate spec IDs
./scripts/build          # Generate HTML only
```

### Version Locations
- Specification version: `meta.yaml` → `versions.specification`
- Protocol version: `meta.yaml` → `versions.protocol`
- Build version: `package.json` → `version`

### Spec Point Prefixes
- `RTL*` - Realtime Library
- `RSC*` - REST Client
- `RSA*` - REST Auth
- `CSV*` - Client Server Versioning
- `CHA-*` - Chat features
- `OB-*` - Objects features
- `TP*` - Test Protocol
- `ENC*` - Encryption

## Contact and Support

- **Issues:** https://github.com/ably/specification/issues
- **Discussions:** Use GitHub Discussions or internal Ably channels
- **SDK Team:** Refer to CONTRIBUTING.md for review processes

---

**Document Version:** 1.0
**Last Updated:** 2026-01-30
**Specification Version at Time of Writing:** 5.0.0
**Protocol Version at Time of Writing:** 5
