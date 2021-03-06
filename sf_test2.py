
import time

from wiske import Synthesizer, EventNoteOn, EventNoteOff
from notenames import name_to_val


synth = Synthesizer()

synth.load_soundfont("/home/james/Downloads/GeneralUserGS/GeneralUserGS.sf2")
# synth.load_soundfont("/home/james/Documents/MuseScore3Development/SoundFonts/MuseScore_General_Lite-v0.1.5/MuseScore_General_Lite.sf2")

inst = synth.new_instrument(0, 0)

SUSTAIN = True
REPITCH = 12

BEAT = 60 / 200

MUSIC = [
    ("G3", BEAT),
    ("C3", BEAT),
    (None, BEAT * 0.5),
    ("C4", BEAT),
    ("A3", BEAT * 0.5),

    ("G3", BEAT),
    ("C3", BEAT),
    (None, BEAT * 0.5),
    ("G3", BEAT),
    ("F3", BEAT * 0.5),

    ("E3", BEAT * 0.5),
    ("E3", BEAT * 0.5),
    ("F3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("C3", BEAT),
    ("D3", BEAT),

    ("E3", BEAT * 4),

    ("G3", BEAT),
    ("C3", BEAT),
    (None, BEAT * 0.5),
    ("C4", BEAT),
    ("A3", BEAT * 0.5),

    ("G3", BEAT),
    ("C3", BEAT),
    (None, BEAT * 0.5),
    ("G3", BEAT),
    ("F3", BEAT * 0.5),

    ("E3", BEAT * 0.5),
    ("E3", BEAT * 0.5),
    ("F3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("C3", BEAT),
    ("D3", BEAT),
    ("C3", BEAT * 4),

    ("B3", BEAT),
    ("E3", BEAT),
    (None, BEAT * 0.5),
    ("C4", BEAT),
    ("B3", BEAT * 0.5),

    ("B3", BEAT * 0.5),
    ("A3", BEAT * 0.5),
    ("A3", BEAT * 0.5),
    ("B3", BEAT * 0.5),
    ("A3", BEAT * 2),

    ("A3", BEAT),
    ("D3", BEAT),
    (None, BEAT * 0.5),
    ("B3", BEAT),
    ("A3", BEAT * 0.5),

    ("A3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("A3", BEAT * 0.5),
    ("G3", BEAT * 2),

    ("G3", BEAT),
    ("C3", BEAT),
    (None, BEAT * 0.5),
    ("C4", BEAT),
    ("A3", BEAT * 0.5),

    ("G3", BEAT),
    ("C3", BEAT),
    (None, BEAT * 0.5),
    ("G3", BEAT),
    ("F3", BEAT * 0.5),

    ("E3", BEAT * 0.5),
    ("E3", BEAT * 0.5),
    ("F3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("C3", BEAT),
    ("D3", BEAT),

    (None, BEAT * 0.5),
    ("E3", BEAT * 0.5),
    ("F3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("C3", BEAT),
    ("D3", BEAT),

    (None, BEAT * 0.5),
    ("E3", BEAT * 0.5),
    ("F3", BEAT * 0.5),
    ("G3", BEAT * 0.5),
    ("C4", BEAT),
    ("D4", BEAT),
    ("C4", BEAT * 4),
]


for note in MUSIC:
    if note[0] is None:
        time.sleep(note[1])
        continue
    note_val = name_to_val(note[0])
    inst.send_event(EventNoteOn(note_val + REPITCH, 100))
    inst.send_event(EventNoteOn(note_val + REPITCH + 4, 100))
    # inst.send_event(EventNoteOn(note_val + REPITCH + 7, 100))

    if SUSTAIN:
        time.sleep(note[1] - 0.05)
    else:
        time.sleep(0.01)

    inst.send_event(EventNoteOff(note_val + REPITCH))
    inst.send_event(EventNoteOff(note_val + REPITCH + 4))
    # inst.send_event(EventNoteOff(note_val + REPITCH + 7))

    if SUSTAIN:
        time.sleep(0.05)
    else:
        time.sleep(note[1] - 0.01)

input()
synth.halt()
