# Ably Features Specification: Contributing Guidelines

## Local Development Workflow

Please use our GitHub workflows ([Check](.github/workflows/check.yaml) and [Assemble]((.github/workflows/assemble.yaml))) as the canonical source of truth for how this codebase is validated and built in CI, however to get you up and running quickly the local development experience goes like this:

### Required Development Tools

You'll need [Ruby](https://www.ruby-lang.org/) and [Node.js](https://nodejs.org/) installed.
Consult [our `.tool-versions` file](.tool-versions) for the versions that we use to validate and build in CI.
This file is of particular use to those using [asdf](https://asdf-vm.com/) or compatible tooling.

### Installing Dependencies

When you've just cloned the repository or you've switched branch, ensure that you've installed dependencies with:

    npm install

[The `scripts` folder](scripts/) contains code written in Ruby, however those scripts are intentionally self-contained, so there is no need to discretely install Ruby dependencies outside of what is done inline in those script files.

### Build and Preview

To build the static HTML microsite that's generated from the source files in this repository:

    npm run build

Then to open that in your browser to preview:

    open output/index.html

On macOS systems that will open it using the `file://` URL loading scheme.
This means that navigating to the folders for each page will require two clicks, first into the folder and then onto the `index.html` document within that folder.

If you make a change to a source file then you will need to `npm run build` again and then refresh your browser.

We plan to improve this developer experience when we work on
[#90](https://github.com/ably/specification/issues/90),
by adding a local development HTTP server.

## Features Spec Points

When making changes to [the spec](textile/features.textile), please follow these guidelines:

- **Ordering**: Spec items should generally appear in ID order, but priority should be placed on ordering them in a way that makes coherent sense, even if that results in them being numbered out-of-order. For example, if `XXX1`, `XXX2` and `XXX3` exist but it would make more sense for `XXX3` to follow `XXX1`, then just move the spec items accordingly without changing their IDs
- **Addition**: When adding a new spec item, choose an ID that is greater than all others that exist in the given section, even if there is a gap in the currently assigned IDs. 
- **Modification**: Spec items should never be mutated, except to patch a mistake that doesn't change the semantics for SDK implementations. Follow the guidance outlined here in respect of _Replacement_ if the meaning or scope of a spec point needs to change.
- **Removal**: When removing a spec item, it must remain but replace all text with `This clause has been deleted as of version Y.Z of this specification`. See [#1057](https://github.com/ably/docs/pull/1057) for an example of this in practice.
- **Replacement**: When replacing a spec item, it must remain but replace all text with `This clause has been replaced by "X":#X as of version Y.Z of this specification`.
- **Deprecation**: Our approach to deprecating features is yet to be fully evolved and documented, however we have a current standard in place whereby the text "(deprecated)" is inserted at the beginning of a specification point to declare that it will be removed in a future release. The likely outcome is that in the next major release of the spec/protocol we'll remove that spec item, per guidance above.

Historically, before the above guidance was established - in particular around _Removal_ and _Replacement_ - there have been some cases where spec points were completely deleted.
This left us open to the problem that client library references to spec items could end up semantically invalid if that spec point was re-used later.
For example, if `XXX1a` and `XXX1c` exist but `XXX1b` doesn’t because it was removed in the past (prior to this guidance being established), then we should introduce `XXX1d` for the new spec item rather than re-using `XXX1b`.

## Release Process

This will be documented when we work on
[#6](https://github.com/ably/specification/issues/6).
