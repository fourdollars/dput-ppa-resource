 [![GitHub: fourdollars/dput-ppa-resource](https://img.shields.io/badge/GitHub-fourdollars%2Fdput%E2%80%90ppa%E2%80%90resource-lightgray.svg)](https://github.com/fourdollars/dput-ppa-resource/) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT) [![Bash](https://img.shields.io/badge/Language-Bash-red.svg)](https://www.gnu.org/software/bash/) ![Docker](https://github.com/fourdollars/dput-ppa-resource/workflows/Docker/badge.svg) [![Docker Pulls](https://img.shields.io/docker/pulls/fourdollars/dput-ppa-resource.svg)](https://hub.docker.com/r/fourdollars/dput-ppa-resource/)
# dput-ppa-resource
[concourse-ci](https://concourse-ci.org/)'s dput-ppa-resource

It only supports the put step.

## Config

### Resource Type

```yaml
resource_types:
- name: resource-dput-ppa
  type: registry-image
  source:
    repository: fourdollars/dput-ppa-resource
    tag: latest
```

or

```yaml
resource_types:
- name: resource-dput-ppa
  type: registry-image
  source:
    repository: ghcr.io/fourdollars/dput-ppa-resource
    tag: latest
```

### Resource

* fingerprint: **Required**
* passphrase: **Required**
* private_key: **Required**
* ppa: Optional. You can provide it later in the put step.

```yaml
resources:
- name: dput
  icon: package-up
  type: resource-dput-ppa
  source:
    ppa: ppa:username/ppa-name
    fingerprint: FingerprintOfGPGKey
    passphrase: PassphraseOfGPGPrivateKey
    private_key: |
    -----BEGIN PGP PRIVATE KEY BLOCK-----
    ...
    ...
    ...
    -----END PGP PRIVATE KEY BLOCK-----
```

### put step

* path: **Required**. Specify a path and all *_source.changes under that path will be signed and dput into the PPA.
* ppa: Optional. You can provide it earlier in the resources.

```yaml
- put: dput
  params:
    ppa: ppa:username/ppa-name
    path: SomeFolderInTask
```
```shell
# It acts like the following commands.
$ echo "$private_key" > private.key
$ echo "$passphrase" | gpg --passphrase-fd 0 --pinentry-mode loopback --import private.key
$ rm private.key
$ find "$path" -name '*_source.changes' | while read -r package; do
> echo "$passphrase" | debsign -p'gpg --passphrase-fd 0 --pinentry-mode loopback' -S -k"$fingerprint" "$package"
> dput "$ppa" "$package"
> done
```
