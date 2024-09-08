#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from kutil.pyngguin import *


def main() -> None:
    window = Window()
    window.title = "Window 1 title"
    window.width = 750
    window.height = 1000

    # window2 = Window()
    # window2.title = "Window 2 title"
    # window2.width = 350
    # window2.height = 500

    cont = Container(parent=window)
    # cont.set_stick(STICK.LEFT | STICK.TOP | STICK.BOTTOM)
    cont.width = 600
    cont.height = 500
    cont.x = 100
    cont.y = 150

    text = Text(parent=cont)
    text.text = "Hello, World!"
    text.x = 100
    text.y = 50

    text2 = Text(parent=cont)
    text2.text = "Hi mum!"
    text2.x = 150
    text2.y = 60

    main_loop()


if __name__ == '__main__':
    main()
