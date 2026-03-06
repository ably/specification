# Ably Features Specification

[![Check](https://github.com/ably/specification/actions/workflows/check.yaml/badge.svg)](https://github.com/ably/specification/actions/workflows/check.yaml)

_[Ably](https://ably.com) is the platform that powers synchronized digital experiences in realtime. Whether attending an event in a virtual venue, receiving realtime financial information, or monitoring live car performance data – consumers simply expect realtime digital experiences as standard. Ably provides a suite of APIs to build, extend, and deliver powerful digital experiences in realtime for more than 250 million devices across 80 countries each month. Organizations like Bloomberg, HubSpot, Verizon, and Hopin depend on Ably’s platform to offload the growing complexity of business-critical realtime data synchronization at global scale. For more information, see the [Ably documentation](https://ably.com/documentation)._

## Overview

This repository has been created as the new home for the 'features spec' that describes the interfaces, implementation details and behaviours of SDKs (sometimes referred to as client libraries) that provide application developers with support to integrate and leverage the Ably platform in their solutions.

## Versions

Defined within the contents of this repository are multiple version numbers:

| Version | Format | Location of Definition | Scope |
| ------- | ------ | ---------------------- | ----- |
| [**Specification**](#specification-version) | [SemVer](https://semver.org/) | The `versions.specification` field in [`meta.yaml`](meta.yaml) | Format and usage are specified in `CSV1`. The specification documents - files in [the `textile/` folder](textile/), the 'content'. |
| [**Protocol**](#protocol-version) | Integer from version `2` onwards (it was Decimal prior to that, for example `1.2`). | The `versions.protocol` field in [`meta.yaml`](meta.yaml) | Format and usage are specified in `CSV2`. The wire protocol used when communicating with the Ably service. Specified for REST requests under `RSC7a` and for Realtime connections under `RTN2f`. Sometimes referred to as 'API version' (when 'API' is referring to details of the protocols understood by the Ably service). |
| [**Build**](#build-version) | [SemVer](https://semver.org/) | The `version` field in [`package.json`](package.json) | Other files hosted in this repository which render the specification for viewers or otherwise check it or build artifacts from it. |

### Specification Version

These documents contain the authorative guidance for developers writing and maintaining SDKs that interact with the Ably service.

Examples of changes that would result in a `major` bump, being backwards incompatible changes, include:

- The SDK API used by app developers has changed in a way that is breaking
- Required SDK behaviour has changed in a way that necessitates that changes are made to SDK implementations
- There is a change to the way that the service interacts with SDKs when they announce compatibility with a newer [protocol version](#protocol-version)

Examples of changes that would result in a `minor` bump, being backwards compatible changes, include:

- The SDK API used by app developers has changed in a way that is backwards compatible (typically a new feature or enhancement)
- There is new required SDK behaviour that only needs SDKs to add new behaviours, without modifying existing ones
- There is a new element of the wire protocol which SDKs may start using in order to offer a new feature/enhancement

Examples of changes that would result in a `patch` bump include:

- Spelling mistake or typo corrections, where the meaning was previously clear and hasn't changed as a result of the fix
- Formatting improvements in the textile markup, where those changes don't alter the way that the rendered output is interpreted
- Improvements intended to make meaning clearer, where the intended meaning has not changed  - clearly these are changes that are likely to be subjective in nature, so it is suggested that these changes are rigorously reviewed by as many individuals as possible

Where the 'SDK API' refers to the IDL and interface names documented in the [features spec](textile/features.textile),
representing the surface area of the SDK that is directly visible to and used by app developers who are using that SDK to use the Ably service.

It is expected that there may be specification changes which involve features spec point _Removal_, _Replacement_ or _Deprecation_ where that change only necessitates a `minor` bump to the specification version number - that is, the impact of the change is deemed backwards compatible according to the constraints outlined above. See [Contributing Guidance: Features Spec Points](CONTRIBUTING.md#features-spec-points).

It is not anticipated that specification versions will ever need to use a pre-release suffix.
The specification is primarily used by SDK developers and bumps to the specification version will only be made after the changes being released have been thoroughly reviewed and likely to have already have been implemented/prototyped in at least one SDK.
Therefore, the idea of a 'preview' release of the specification doesn't make sense.

See also:

- [Ably SDK Team: Guidance on Releases: Version Bump](https://github.com/ably/engineering/blob/main/sdk/releases.md#version-bump)

### Protocol Version

Incremented when changes are made to the Ably service where at least one of the following applies:

- the wire protocol API has changed
- the behaviour of the service has changed in a way that SDKs need to reflect or respond to
- the behaviour of the SDK needs to change in a way that the service needs to reflect or respond to

We are using a simple integer value here because there is no need for structured versioning.
When an SDK adopts a new protocol version then it's 'all or nothing', in that all implications of supporting that protocol version must be catered for by the changes made to that SDK in order to adopt the new protocol version.

Whether SDK changes are as a result of wire protocol changes that are breaking (incompatible) or enhancing in nature is not something that we need the protocol version to imply by its value.
The Ably service promises to support SDKs connecting to it using older protocol versions.
This 'service makes right' feature of the service means that all we need the protocol version for is to track when a behavioural change has been made to the service implementation, alongside its corresponding wire protocol API, that requires the service to know that the SDK it's communicating with also understands this new behaviour.

### Build Version

This code (including `.js`, Ruby, `.html.hbs` and `.css` files) has been written specifically to read and process the files contained in this repository that contain specification content.
Variously they may be referred to as 'build tools' or 'toolchain'.

For the time being there is no exposure of these tools outside of this repository - that is, they are used for [local development](CONTRIBUTING.md#local-development-workflow) and are also executed from our [GitHub workflows](.github/workflows/).
For this reason, we have no need to have any formal release process for them.
The `1.0.0` value for `version` specified in [`package.json`](package.json) carries nominal importance and will remain static until we get to a point of needing it to change, for example if we end up exporting an npm package from here.

## Future Direction for Specification Point Adherence Tracking

We have
[this Google Sheets document](https://docs.google.com/spreadsheets/d/1ZbAfImxRLRKZNe4KPX7b_0BVVI-qyqnvbAco5TFWSQU/edit?usp=sharing)
which has been used at Ably, by client library SDK developers,
to indicate adherence to individual
[feature specification points](https://sdk.ably.com/builds/ably/specification/main/features/)
by their
SDK source codebase.
_Request permission from your Manager if you would like access to this spreadsheet._

The detail captured in that spreadsheet is an important source of information which should be able to help us understand the level of features specification compliance across our SDKs. As such, it should be considered a valuable source of truth when it comes to working out what features are implemented across our SDKs.

Additionally, it is very likely that we will continue to want to track feature specification point adherence, at that level of fine granularity, going forwards.

What is clear, however, is that a Google Sheets document is probably not the appropriate venue to continue tracking this information. Instead, the currently anticipated solution is that we export the information per-SDK from that spreadsheet and represent it in a simple format as a 'feature specification point adherence checklist' (/ manifest) in each SDK source code repository (CSV, YAML or some other logical textual data format). This would be instantiated via an initial snapshot process, after which it could be evolved atomically as an additional part of the source code of that SDK, with the spreadsheet becoming obsolete once all SDKs have been exported.

## Contributing

For guidance on how to contribute to this project, see [CONTRIBUTING.md](CONTRIBUTING.md).
