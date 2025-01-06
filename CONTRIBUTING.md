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
- **Structuring**: When structuring the specification and defining the relationships between clauses and subclauses, generally avoid placing behavior descriptions and implementation details in the parent clause. The parent clause should primarily serve as an informational header for its subclauses. However, if it improves coherence, including behavior descriptions in the parent clause is permissible.
- **Clarity**: Refrain from using conditional statements and multiple behavior descriptions within a single spec item. These should be separated into distinct subclauses for clarity.
- **Addition**: When adding a new spec item, choose an ID that is greater than all others that exist in the given section, even if there is a gap in the currently assigned IDs.
- **Modification**: Spec items should never be mutated, except to patch a mistake that doesn't change the semantics for SDK implementations. Follow the guidance outlined here in respect of _Replacement_ if the meaning or scope of a spec point needs to change.
- **Removal**: When removing a spec item, it must remain but replace all text with `This clause has been deleted. It was valid up to and including specification version @X.Y@.` (uses textile markup).
- **Replacement**: When replacing a spec item, it must remain but replace all text with `This clause has been replaced by "@Z@":#Z. It was valid up to and including specification version @X.Y@.` (uses textile markup).
- **Deprecation**: Our approach to deprecating features is yet to be fully evolved and documented, however we have a current standard in place whereby the text "(deprecated)" is inserted at the beginning of a specification point to declare that it will be removed in a future release. The likely outcome is that in the next major release of the spec/protocol we'll remove that spec item, per guidance above.

### Additional Notes on Features Spec Point _Removal_ and _Replacement_

Specification version references included in _Removal_ and _Replacement_ notices are in the form `X.Y` because they only need to include the `major` (`X`) and `minor` (`Y`) components of the specification version. See [Specification Version](README.md#specification-version).

If the clause being removed or replaced has subclauses then the expected implication is that they are also being removed or replaced. Therefore, aligned with this guidance, they must remain but with their text replaced. This might mean that in some cases, for example, a clause is marked as replaced but some or all of its subclauses are marked as removed.

Variations on the replacement text for removed or replaced spec items is allowed, as long as the overarching structure remains the same. For example:

- When a spec item has been removed because a new spec point has made it redudant, which is the case for `RTN15f` after specification version `1.2`, where the replacement text is: `This clause has been deleted (redundant to "RTN19a":#RTN19a). It was valid up to and including specification version @1.2@.`
- When a spec item has been replaced by more than one new spec item, which is the case for `RTN16b` after specification version `1.2`, where the replacement text is: `This clause has been replaced by "@RTN16g@":#RTN16g and "@RTN16m@":#RTN16m. It was valid up to and including specification version @1.2@.`

Historically, before the above guidance was established - in particular around _Removal_ and _Replacement_ - there have been some cases where spec points were completely deleted.
This left us open to the problem that client library references to spec items could end up semantically invalid if that spec point was re-used later.
For example, if `XXX1a` and `XXX1c` exist but `XXX1b` doesn’t because it was removed in the past (prior to this guidance being established), then we should introduce `XXX1d` for the new spec item rather than re-using `XXX1b`.

## SDK API docstrings

The `api-docstrings.md` file is a set of language-agnostic reference API commentaries for SDK developers to use when adding docstring comments to Ably SDKs. For new fields, this file should be modified in the same PR that makes the spec changes for those fields.

Modifications should obey the following conventions:

### Table format

#### Classes

The table for each class contains the following columns:

```
| Method / Property | Parameter | Returns | Spec | Description |
```

* **Method/Property**: The full method signature (code formatted only where necessary, e.g. where it includes `<`, or property name.
* **Parameter**: Each parameter should have its own row and be code formatted.
* **Returns**: The return value should be code formatted and has its own row, after the parameters have been listed.
* **Spec**: The spec point related to the method or property.
* **Description**: The language-agnostic description that will form the docstrings.

#### Enums

The table for each enum contains the following columns:

```markdown
| Enum | Spec | Description |
```

* **Enum**: The name of each value for the enum.
* **Spec**: The spec point related to the enum.
* **Description**: The language-agnostic description that will form the docstrings.

### Conventions

The following conventions should be followed when adding a new method or property to the table:

* Use a verb with an `s` for method descriptions. Common uses are:
    * `get` --> `retrieves`
    * `subscribe` --> `registers (a listener)`
    * `publish` --> `Publishes`
* The expression key-value pairs should be hyphenated.
* Parameters or returns that refer to another class are referred to in terms of objects, for example:
    ```
    A [`Channels`]{@link Channels} object.
    ```

* Links to other classes/enums are written in the format:
    ```
    [`<text>`]{@link <class>#<property>}
    ```

    For example:
    ```
    [`ClientOptions.logLevel`]{@link ClientOptions#logLevel}`
    ```
* If a method references its own class, it should just be code formatted, and not link to itself.
* Descriptions can link out to conceptual docs hosted on `ably.com/docs`, but should never link to the API references hosted there.
* A class or object should always be capitalized.
* Methods and parameters should always be lower-case.
* If adding a method/property to separate REST and realtime classes, ensure the descriptions are consistent (where possible).
* When a return value is returned in a paginated list, the description should link to the PaginatedResult class, as well as the class of whatever is returned.
* Items deprecated in the features spec should include the following text at the beginning of the description: `DEPRECATED: this <property/method> is deprecated and will be removed in a future version.`
* Default values should be listed in the description field.
* If a minimum or maximum value exists for a parameter then it should be listed in the description field.
* Time values should be referred to as `milliseconds since the Unix epoch` where applicable.

## Release Process

Use our standard [Release Process](https://github.com/ably/engineering/blob/main/sdk/releases.md#release-process), where:

- there is no 'Publish Workflow' to be triggered in this repository
- the version to be bumped in the release branch is the [Specification Version](README.md#specification-version)
- in addition to pushing a full Git version tag (to persist as static and immutable) in the form `v<major>.<minor>.<patch>`, tags should also be added or moved for higher levels of specification version granularity:
  - `v<major>.<minor>` - e.g. `v1.2` for latest patch to version 1.2 of the specification
  - `v<major>` - e.g. `v2` for the latest enhancements and patches to version 2 of the specification

It's worth emphasising here, for clarity, that bumps to the [Protocol Version](README.md#protocol-version) or [Build Version](README.md#build-version) are not part of the release process and do not appear in release branches or the pull requests that represent those release branches. If these versions need to be bumped then that is done as part of a feature change or addition, where that feature is then subsequently implicitly incorporated into a release at the time of executing the release process.
