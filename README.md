#linuxportal-api-kernel

Basic module that is subclassed everywhere to provide a consistent class interface.

All dependent modules must always expose the following functions:

* `create()`
* `read()`
* `update()`
* `delete()`
* `list()`

## Modules

### `lp_api_kernel.internal.BaseInternalApi`

### `lp_api_kernel.external.BaseExternalApi`