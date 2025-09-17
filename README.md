# KUtil

Kuba's Python Utilities (kutil is intentional - a Czech word).
Made for Python 3.12 and newer

# Installation from PyPI

Sadly, the name `kutil` is already used, but I sneaked it to PyPI with a different name: `KUtil-jakubaugustyn`

```cmd
pip3 install KUtil-jakubaugustyn
```

See it on PyPI [here](https://pypi.org/project/KUtil-jakubaugustyn/).

# Installation

To manually install KUtil, download the repository [here](https://github.com/kubikaugustyn/KUtil) and copy
the `src/kutil` folder from the repo directly to your interpreter's `Lib` folder.

# Installation&development on the same machine

If you want to use and develop Kutil, you must clone github repository and link it inside of your interpreter's `Lib`
folder
using command like this:

```console
mklink /d C:\Python312\Lib\kutil "C:\Users\user\path\to\folder\KUtil\kutil"
```

# Features

## kutil.buffer

### ByteBuffer

ByteBuffer is a basic class, extending the functionality of a native `bytearray` with a read pointer, read and write
safety and the ability to upgrade it to a DataBuffer.

```python
# Import the class(es)
from kutil import ByteBuffer, MemoryByteBuffer, FileByteBuffer, readFile
# OR specifically:
from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer

# Init the buffer:
buff: ByteBuffer = MemoryByteBuffer(b'input data')  # Creates a buffer with the data
# OR
buff: ByteBuffer = MemoryByteBuffer(10)  # Creates a buffer with 10 nulled bytes, keeping the reading pointer at 0
# OR
buff: ByteBuffer = FileByteBuffer(open("file.bin", "wb"))  # Creates a buffer wrapping a file handle (BinaryIO)
# OR
buff: ByteBuffer = readFile("file.bin", "buffer")  # The same functionality as above, but nicer

# Write at the end of the buffer:
buff.writeByte(69)  # Writes a single byte at the end of the buffer
buff.write(b'hello')  # Writes an integer iterable at the end of the buffer
buff.write(..., i=2)  # Writes to index 2 of the buffer, moving the data after it

# Read from the buffer:
byte = buff.readByte()  # Reads a single byte at the pointer, advancing the pointer accordingly
data = buff.read(5)  # Reads 5 bytes at the pointer, advancing the pointer accordingly

# Export the data from the buffer properly:
allData = buff.export()

# Reset the buffer properly:
buff.reset()

# Advanced functions:
buff.has(5)  # Check whether we can read 5 bytes from the buffer
buff.has(-5)  # Check whether we can undo by 5 bytes in the buffer
buff.assertHas(5)  # Same as buff.has(), but throws an error instead of returning False
buff.back(5)  # Moves the pointer back by 5 bytes
buff.skip(5)  # Moves the pointer forward by 5 bytes
buff.readLine()  # Reads the next line, omitting the newline bytes, but skipping them
buff.readRest()  # Reads all the bytes left in the buffer
buff.resetPointer()  # Moves the pointer to the beginning (0)
# and more...

# And always remember to destroy the buffer when you're done with it, to prevent memory leaks, open file handles, etc.
buff.destroy()
```

### DataBuffer

DataBuffer is a class extending the functionality of a ByteBuffer with a writing ints, strings, etc. and the ability
to downgrade it to a ByteBuffer.

Note that every number is **big endian**!

```python
# Import the class
from kutil import DataBuffer, ByteBuffer
# OR
from kutil.buffer.DataBuffer import DataBuffer, ByteBuffer

# Init the buffer:
dBuff = DataBuffer()  # Creates a blank data buffer
# OR
buff: ByteBuffer = ...
dBuff = DataBuffer(buff)  # Upgrades a buffer to a data buffer

# Write ints:
# Unsigned - writeUInt<n>() where n is the amount of bits
dBuff.writeUInt32(69)
# Signed - writeInt<n>()
dBuff.writeInt64(69)
# Arbitrary byte size
dBuff.writeUInt(69, byteSize=3)
dBuff.writeInt(69, byteSize=3)

# Read ints (same naming as when writing):
num = dBuff.readUInt32()
num2 = dBuff.readInt16()

# Downgrade to the underlying buffer properly:
buff: ByteBuffer = dBuff.buff

# Reset the buffer properly:
dBuff.reset()

# For advanced functions, see the source code.
```

### AppendedByteBuffer

AppendedByteBuffer is an advanced ByteBuffer that can be used to concatenate/append buffers. The buffers can't be
modified (e.g., their length must not change), and you can add more to the AppendedByteBuffer by passing a ByteBuffer to
the `ByteBuffer.write()` method. However, a better and cleaner way is to use
`ByteBuffer.appended(buffers: Iterable[ByteBuffer], ...): ByteBuffer`, which can perform significant optimizations. This
function can however only be used in cases where you can change the 'buff' reference (e.g., your function returns a
ByteBuffer). If not, and you're only provided a ByteBuffer as an argument, you must use `buff.write(otherToAppend)` as
described above,

```python
# Import the classes
from kutil import ByteBuffer, MemoryByteBuffer, readFile, AppendedByteBuffer
# OR specifically:
from kutil.buffer.AppendedByteBuffer import AppendedByteBuffer

# Init the buffers:
buff1: ByteBuffer = MemoryByteBuffer(b'some header')  # Creates a buffer with some imaginary headers
buff2: ByteBuffer = readFile("file.bin", "buffer")  # And the body

# Now, append the buffers:
buff: ByteBuffer = ByteBuffer.appended([buff1, buff2])  # Creates a buffer with the headers and the body
print(buff.export())  # <<< some header + file contents


# Or, if you can't change the 'buff' reference:
def write(buff: ByteBuffer) -> None:
    buff.write(buff1)
    buff.write(buff2)

# And always remember to destroy the buffer
buff.destroy()
```

### Serializable

Serializable is an abstract class marking a class as being serializable. That means that the class implements the read
and write methods. These classes are mainly used to implement various kinds of packets.

```python
# Import the class
from kutil import Serializable, ByteBuffer
# OR
from kutil.buffer.Serializable import Serializable


class MyStruct(Serializable):
    data: bytes  # An example field to show the usage

    def read(self, buff: ByteBuffer):
        # Read your data from the provided buffer, upgrade to a DataBuffer if needed

        self.data = bytes(buff.read(buff.readByte()))  # Reads a length-prefixed bytes field

    def write(self, buff: ByteBuffer):
        # Write your data to the provided buffer. Do not go back or read from it in any way!

        buff.writeByte(len(self.data)).write(self.data)
```

## kutil.io

### File helpers

The `kutil.io.file` helper module serves as a collection of file helpers.

```python
# Import the functions (you can use import ... from ... too)
import kutil.io.file as f

text = f.readFile("/path/to/file", "text")  # Loads a file as raw text
data = f.readFile("/path/to/file", "json")  # Loads a file as json

f.writeFile("/path/to/file", "Hello world")  # Writes raw text to file
f.writeFile("/path/to/file", {})  # Writes JSON to file

# f.NL and its bytes representation f.bNL are set with
f.changeNewline("CRLF")  # Sets the CRLF scheme

# Get file names and extensions
filename, extension = f.splitFileExtension("/path/to/file")
filename = f.getFileName("/path/to/file")
extension = f.getFileExtension("/path/to/file")
```

### Directory helpers

The `kutil.io.directory` helper module serves as a collection of directory helpers.

```python
# Import the functions (you can use import ... from ... too)
import kutil.io.directory as d

# Iterate over directory files or subdirectories
fileIter = d.enumFiles("/path/to/dir", extendedInfo=False)
subdirIter = d.enumDirs("/path/to/dir", extendedInfo=False)

# Get directory's parent
parent = d.getDirParent("/path/to/dir")
```

## kutil.iterator_help

The `kutil.iterator_help` helper module serves as a collection of iteration helpers.
For now, it only contains a float range.

### rangeFloat()

Arguments are defined in the function docstring, but to summarize:

**There are two ways of calling rangeFloat():**

- `rangeFloat(end, **kwargs)` - will loop from 0 (inclusive) to end (exclusive)
- `rangeFloat(start, end, **kwargs)` - will loop from start (inclusive) to end (exclusive)

**The keyword arguments are the following:**

- `step` - the change per iteration
- `toFloat` - yield float or decimal.Decimal objects?
- `precision` - how precise do you want it to be. If set to 3, you can store 3.14
- `eMax` - the maximum value for the e notation: 1.1e+69
- `eMin` - the minimum value for the e notation: 1.1e-69

All floats provided to the function must NOT be of the float type. They must be one of the following:

- `int` - an integer
- `str` - a string version of the float
- `decimal.Decimal` - the actual format of the value that is used internally to manage the precision etc.

**Here are two examples of the float range usage:**

```python
from kutil.iterator_help import rangeFloat

for i in rangeFloat(1, step=".1", toFloat=True):
    print(i)  # Will go through 0, 0.1, 0.2, ..., 0.9

for i in rangeFloat(1, -1, step="-.5", toFloat=True):
    print(i)  # Will go through 1, 0.5, 0, -0.5
```

## kutil.progress

The `kutil.progress` module serves as a collection of progress bar printing helpers.
For now, it only contains a ProgressBar class and a progress factory.

### ProgressBar

**The arguments are the following:**

- `maxProgress` - The maximum progress value the ProgressBar can reach
- `title` - (optional) The title of the ProgressBar to show on a line before the ProgressBar
- `width` - The width of the ProgressBar's actual bar characters. To get the maximum possible width in characters, read
  the `maxWidth` property.
- `showPercentage` - Whether the ProgressBar should show how many % have already "passed"
- `showProgressCount` - Whether the ProgressBar should show the "progress/maxProgress" values
- `deleteBarOnEnded` - Whether the ProgressBar should be deleted after calling the `end()` function. It has nothing to
  do with the `delete()` function. It deletes the bar line (not the title if provided) so the output is less polluted.

You can always get and set the arguments of the ProgressBar, so you don't have to provide all arguments when creating
the object, although they can only be changed before the `begin()` call or after the `end()` call and before `delete()`
is called.

**Here are two examples of the ProgressBar usage:**

```python
from kutil.progress import ProgressBar
from time import sleep

# You can either create the bar manually - begin(), repeatedly update(x) and then end()
progress: ProgressBar = ProgressBar(10, "Loading", width=10, showProgressCount=True)
progress.begin()
for _ in range(10):
    progress.update(1)
    sleep(.5)
progress.end()

# Or you can only call update(x) using a context manager by using the with statement
with ProgressBar(10, "Loading within WITH", width=10, showProgressCount=True) as bar:
    for _ in range(10):
        bar.update(1)
        sleep(.5)
```

### progressFactory()

**The arguments are:**

- Those provided to the initial call to progressFactory()
- Those provided to the call to the ProgressBarFactory (returned by the initial call to progressFactory())

**The arguments are used in this order:**

1. The arguments provided to the call to the ProgressBarFactory (returned by the initial call to progressFactory())
2. The arguments provided to the initial call to progressFactory() - these are overwritten by the higher priority
   arguments above

**Here is an example of the progress factory usage:**

```python
from kutil.progress import progressFactory, ProgressBarFactory
from time import sleep

# We set up our preferred settings at one place
factory: ProgressBarFactory = progressFactory(maxProgress=10,
                                              width=10, showPercentage=True,
                                              showProgressCount=True, deleteBarOnEnded=True)

for n in range(1, 6):  # Let's pretend we're looping over a list of URLs to download
    # Then we just overwrite some arguments to get our desired ProgressBar
    with factory(title=f"Loading with factory #{n}") as bar:
        for _ in range(10):  # And pretend that we're downloading the file here
            bar.update(1)
            sleep(.1)
```

## kutil.pyngguin

The `kutil.pyngguin` package is a **Py**thon **N**ext **Generation** **GUI** package for **N**erds.

# TODO

This readme is TODO — not all features may be covered yet. Don't worry and contact me if you are uncertain regarding
some behavior, functions or classes.
