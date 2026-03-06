# Content Move from `ably/docs`

## Overview

On 20 September 2022 this [`textile/` folder](./) was pushed to this repository, along with Git commit history relating only to the files contained within.

## How

All steps carried out by [Quintin Willison](https://github.com/QuintinWillison), exactly as described below...

First, the [git-filter-repo](https://github.com/newren/git-filter-repo) tool was used.
It was installed on local machine (macOS 12.2.1) via Homebrew with:

    brew install git-filter-repo

And then a local, clean clone of the `ably/docs` repository was made in a temporary folder and the tool was run with:

```sh
#!/bin/sh
set -e

git clone git@github.com:ably/docs.git

cd docs

git rev-parse HEAD
git rev-parse --short HEAD

git filter-repo \
    --path content/client-lib-development-guide/ \
    --path-rename 'content/client-lib-development-guide/':'textile/'
```

Generating the following output:

```
Cloning into 'docs'...
remote: Enumerating objects: 44063, done.
remote: Counting objects: 100% (216/216), done.
remote: Compressing objects: 100% (181/181), done.
remote: Total 44063 (delta 73), reused 94 (delta 32), pack-reused 43847
Receiving objects: 100% (44063/44063), 207.69 MiB | 3.30 MiB/s, done.
Resolving deltas: 100% (31958/31958), done.
aa02908896d7af2c95ac08fdaaf6e124ca742a07
aa029088
Parsed 6077 commits
New history written in 1.49 seconds; now repacking/cleaning...
Repacking your repo and cleaning out old unneeded objects
HEAD is now at 7772adbc Merge pull request #1530 from ably/tp4-and-tm3-clarification
Enumerating objects: 4502, done.
Counting objects: 100% (4502/4502), done.
Delta compression using up to 16 threads
Compressing objects: 100% (1275/1275), done.
Writing objects: 100% (4502/4502), done.
Total 4502 (delta 2225), reused 4502 (delta 2225), pack-reused 0
Completely finished after 6.78 seconds.
```

To combine this with this repository, [these instructions](https://jeffkreeftmeijer.com/git-combine/) were used...

Then, from a local up-to-date instance of this repository, a temporary remote was added using:

    git remote add temp-docs ~/code/TEMP/docs

A `git fetch` was run:

    git fetch temp-docs

And the merge commit then created:

    git merge temp-docs/main --allow-unrelated-histories

And then pushed to `origin` (GitHub, this repository).

## Issues Transfer

All steps carried out by [Quintin Willison](https://github.com/QuintinWillison), exactly as described below...

Using [GitHub CLI](https://github.com/cli/cli) and [jq](https://github.com/stedolan/jq)...

First, discovering that there were 74 issues in `ably/docs` with the `client-lib-spec` label:

    gh issue list --label client-lib-spec --limit 100

The output of that command is human readable.
The next step was to get it in JSON form:

    gh issue list --label client-lib-spec --limit 100 --json number > client-lib-spec-issue-numbers.json

Generating `client-lib-spec-issue-numbers.json` with the following contents:

```json
[{"number":1607},{"number":1568},{"number":1484},{"number":1476},{"number":1425},{"number":1416},{"number":1347},{"number":1329},{"number":1326},{"number":1291},{"number":1290},{"number":1289},{"number":1288},{"number":1251},{"number":1244},{"number":1165},{"number":1149},{"number":1103},{"number":1100},{"number":1076},{"number":1072},{"number":1069},{"number":1046},{"number":1043},{"number":1000},{"number":991},{"number":984},{"number":977},{"number":976},{"number":918},{"number":895},{"number":894},{"number":891},{"number":889},{"number":805},{"number":791},{"number":762},{"number":754},{"number":705},{"number":693},{"number":669},{"number":667},{"number":652},{"number":646},{"number":628},{"number":627},{"number":619},{"number":595},{"number":577},{"number":566},{"number":543},{"number":468},{"number":467},{"number":455},{"number":435},{"number":429},{"number":425},{"number":404},{"number":391},{"number":359},{"number":349},{"number":343},{"number":335},{"number":334},{"number":332},{"number":326},{"number":325},{"number":280},{"number":263},{"number":224},{"number":202},{"number":149},{"number":141},{"number":36}]
```

Next was to extract just the issue numbers from that JSON document:

    jq '.[] | .number' < client-lib-spec-issue-numbers.json > client-lib-spec-issue-numbers.txt

Then create a script file containing the commands to be run to perform the issue transfers to their new home in the `ably/specification` repository:

    sed -E "s/^(.*)$/gh issue transfer \1 ably\/specification/g" < client-lib-spec-issue-numbers.txt > transfer-client-lib-spec-issues.sh

Then make that script file executable and run it:

```
docs % chmod +x transfer-client-lib-spec-issues.sh
docs % ./transfer-client-lib-spec-issues.sh
https://github.com/ably/specification/issues/13
https://github.com/ably/specification/issues/14
https://github.com/ably/specification/issues/15
https://github.com/ably/specification/issues/16
https://github.com/ably/specification/issues/17
https://github.com/ably/specification/issues/18
https://github.com/ably/specification/issues/19
https://github.com/ably/specification/issues/20
https://github.com/ably/specification/issues/21
https://github.com/ably/specification/issues/22
https://github.com/ably/specification/issues/23
https://github.com/ably/specification/issues/24
https://github.com/ably/specification/issues/25
https://github.com/ably/specification/issues/26
https://github.com/ably/specification/issues/27
https://github.com/ably/specification/issues/28
https://github.com/ably/specification/issues/29
https://github.com/ably/specification/issues/30
https://github.com/ably/specification/issues/31
https://github.com/ably/specification/issues/32
https://github.com/ably/specification/issues/33
https://github.com/ably/specification/issues/34
https://github.com/ably/specification/issues/35
https://github.com/ably/specification/issues/36
https://github.com/ably/specification/issues/37
https://github.com/ably/specification/issues/38
https://github.com/ably/specification/issues/39
https://github.com/ably/specification/issues/40
https://github.com/ably/specification/issues/41
https://github.com/ably/specification/issues/42
https://github.com/ably/specification/issues/43
https://github.com/ably/specification/issues/44
https://github.com/ably/specification/issues/45
https://github.com/ably/specification/issues/46
https://github.com/ably/specification/issues/47
https://github.com/ably/specification/issues/48
https://github.com/ably/specification/issues/49
https://github.com/ably/specification/issues/50
https://github.com/ably/specification/issues/51
https://github.com/ably/specification/issues/52
https://github.com/ably/specification/issues/53
https://github.com/ably/specification/issues/54
https://github.com/ably/specification/issues/55
https://github.com/ably/specification/issues/56
https://github.com/ably/specification/issues/57
https://github.com/ably/specification/issues/58
https://github.com/ably/specification/issues/59
https://github.com/ably/specification/issues/60
https://github.com/ably/specification/issues/61
https://github.com/ably/specification/issues/62
https://github.com/ably/specification/issues/63
https://github.com/ably/specification/issues/64
https://github.com/ably/specification/issues/65
https://github.com/ably/specification/issues/66
Message: Something went wrong while executing your query. Please include `CB4D:1A37:932D5C:953E2E:633ACCF7` when reporting this issue., Locations: []
https://github.com/ably/specification/issues/67
Message: Something went wrong while executing your query. Please include `CB4F:86BE:8D6217:8F785C:633ACCF9` when reporting this issue., Locations: []
https://github.com/ably/specification/issues/68
Message: Something went wrong while executing your query. Please include `CB51:86BE:8D6D04:8F835E:633ACCFB` when reporting this issue., Locations: []
Message: Something went wrong while executing your query. Please include `CB52:48BB:900647:921323:633ACCFD` when reporting this issue., Locations: []
https://github.com/ably/specification/issues/69
https://github.com/ably/specification/issues/70
https://github.com/ably/specification/issues/71
https://github.com/ably/specification/issues/72
Message: Something went wrong while executing your query. Please include `CB57:85E8:A5B0E3:A7CC7A:633ACD04` when reporting this issue., Locations: []
https://github.com/ably/specification/issues/73
https://github.com/ably/specification/issues/74
Message: Something went wrong while executing your query. Please include `CB5A:5B59:961B4A:982946:633ACD08` when reporting this issue., Locations: []
Message: Something went wrong while executing your query. Please include `CB5B:5F67:A0C56B:A2E241:633ACD0A` when reporting this issue., Locations: []
https://github.com/ably/specification/issues/75
Message: Something went wrong while executing your query. Please include `CB5D:5B59:962B05:98392D:633ACD0C` when reporting this issue., Locations: []
Message: Something went wrong while executing your query. Please include `CB5E:B2EB:8ECEEC:90E528:633ACD0E` when reporting this issue., Locations: []
Message: Something went wrong while executing your query. Please include `CB5F:57ED:8FB458:91C1EA:633ACD0F` when reporting this issue., Locations: []
Message: Something went wrong while executing your query. Please include `CB60:85E8:A5E3AC:A80001:633ACD10` when reporting this issue., Locations: []
?1 docs %
```

Clearly some failures, with 11 issues remaining in `ably/docs` after the script completed:

```
docs % gh issue list --label client-lib-spec --limit 100

Showing 11 of 11 issues in ably/docs that match your search

#435  40140 Timestamp not current ideas                                                        client-lib-spec, knowledge-base, no-sync                  about 2 months ago
#425  Show a warning when invalid options are used in dynamic languages                        content-request, client-lib-spec, no-sync                 about 2 months ago
#391  [Proposal] Channel events received on non-attached channels                              content-request, client-lib-spec, no-sync                 about 2 months ago
#359  Only log outcome from client library retries to fallback hosts                           content-request, client-lib-spec, no-sync                 about 8 months ago
#332  [Proposal] Add echoMessages flag at the channel level                                    client-lib-spec, no-sync                                  about 2 months ago
#280  Add requirement to the spec that new fields should not break existing libraries          content-request, client-lib-spec, no-sync                 about 2 months ago
#263  Add support for strict flag for tokenRequests                                            content-request, api-reference, client-lib-spec, no-sync  about 2 months ago
#202  Consider mechanism to dynamically change next retry for disconnected / suspended states  content-request, client-lib-spec, no-sync                 about 2 months ago
#149  Spec: Ensure terminal states have no effect on listeners                                 client-lib-spec, no-sync                                  about 2 months ago
#141  Add spec for lexicographic ordering                                                      client-lib-spec, no-sync                                  about 2 months ago
#36   Bundling & queueing                                                                      content-request, client-lib-spec, no-sync                 about 2 months ago
```

My working theory was that the failures were perhaps due to rate limiting.
I suspect that may have been the case, as simply running through the whole process again from the top resulted in success:

```
docs % ./transfer-client-lib-spec-issues.sh
https://github.com/ably/specification/issues/76
https://github.com/ably/specification/issues/77
https://github.com/ably/specification/issues/78
https://github.com/ably/specification/issues/79
https://github.com/ably/specification/issues/80
https://github.com/ably/specification/issues/81
https://github.com/ably/specification/issues/82
https://github.com/ably/specification/issues/83
https://github.com/ably/specification/issues/84
https://github.com/ably/specification/issues/85
https://github.com/ably/specification/issues/86
```
