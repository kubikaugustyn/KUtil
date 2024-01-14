# KUtil

Kuba's Python Utilities (kutil is intentional - a Czech word).
Made for Python

# Installation from PyPI

Sadly, the name *kutil* is already used, see [#3](https://github.com/kubikaugustyn/KUtil/issues/3) for more info, but
right now KUtil cannot be installed from PyPI.

[//]: # (```cmd)

[//]: # (pip3 install kutil)

[//]: # (```)

# Installation

To manually install KUtil, download the repository [here](https://github.com/kubikaugustyn/KUtil) and copy
the `src/kutil` folder from the repo directly to your interpreter's `Lib` folder.

# Installation&development on the same machine

If you want to use and develop Kutil, you must clone github repository and link it inside of your interpreter's `Lib`
folder
using command like this:

```console
mklink /d C:\Python312\Lib\kutil "C:\Users\user\path\to\folder\KUtil\src\kutil"
```
