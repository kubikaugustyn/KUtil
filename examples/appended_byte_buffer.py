#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import tempfile

from kutil import ByteBuffer, MemoryByteBuffer, FileByteBuffer, AppendedByteBuffer, NL


def main(file) -> None:
    buff1: ByteBuffer = FileByteBuffer(file)
    buff1.write(b'part 1')
    buff2: ByteBuffer = MemoryByteBuffer()
    buff2.write(b'part 2')

    appended1 = ByteBuffer.appended([buff2, buff1], customThreshold=0)
    print("Mid-point:", appended1.export())

    buff3: ByteBuffer = MemoryByteBuffer(b'part 3')
    buff4: ByteBuffer = MemoryByteBuffer(b'part 4')

    fullBuff: ByteBuffer = ByteBuffer.appended(
        buffers=[appended1, buff3, buff4],
        customThreshold=5,
    )
    fullBuff.write(b'part 5')
    print("Full buffer:", fullBuff)
    print("Appended contents:", fullBuff.export())


def main2(file) -> None:
    body: ByteBuffer = FileByteBuffer(file)
    body.write(b'Hello, world! This is a very large file!!!!!')

    def pack(buff: ByteBuffer) -> None:
        buff.write(b'HTTP/1.1 200 OK\r\n')
        buff.write(b'Content-Type: text/plain\r\n')
        buff.write(b'Content-Length: ').write(str(body.fullLength()).encode('ascii')).write(b'\r\n')
        buff.write(b'\r\n')
        buff.write(body)

    packed: ByteBuffer = AppendedByteBuffer()
    pack(packed)
    print("Full buffer:", packed)
    print("Packed contents:", packed.export())
    print(packed.export().decode('ascii'))

    print(f"{NL}{NL}Byte-by-byte check:")
    packed.resetPointer()
    for _ in range(packed.fullLength()):
        print(chr(packed.readByte()), end='')

    print(f"{NL}{NL}Chunk-by-Chunk check:")
    packed.resetPointer()
    for batch in packed.batched(10):
        print(batch.decode('ascii'), end='')


if __name__ == '__main__':
    with tempfile.TemporaryFile(mode="wb+") as f:
        # main(f)
        main2(f)
