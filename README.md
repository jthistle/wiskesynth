# Wiske

Wiske (pronounced /ˈwɪskə/) is a synthesizer written in Python, for use in Python programmes.

It is still in early development, but can already play, to some degree, soundfonts in the sf2 format.

Wiske currently only supports Linux, but I hope to target Windows and Mac as well in the future.

Wiske originated as a synthesizer for sister-project [Tabby](https://github.com/jthistle/tabby), an ASCII guitar tab editor.

## Speed and reliability

Wiske is constantly improving in its speed. Try out the stress test (you'll need to get hold
of a soundfont and set its location in the code for it to work properly).

Running with the vanilla Python interpreter, you can get about 30-ish notes playing simultaneously, currently.

Running with PyPy, it can play over 150 notes simultaneously! Seriously, if you want any kind of real performance
out of this thing, **you need to run it with PyPy**.

## Structure

The main module is in `/wiske`.

A couple of demos/manual tests are in the root directory as `sf_test*.py`.

## Docs

There are none! There will be some!
