
from wiske import Synthesizer, EventNoteOn, EventNoteOff

NOTE = 50

synth = Synthesizer()

synth.load_soundfont("/home/james/Downloads/GeneralUserGS/GeneralUserGS.sf2")
# synth.load_soundfont("/home/james/Documents/MuseScore3Development/SoundFonts/MuseScore_General_Lite-v0.1.5/MuseScore_General_Lite.sf2")

inst = synth.new_instrument(0, 48)

print(synth.sfont.presets_list_user())
print("ready")

# Seems to be about the maximum possible notes at the moment
NOTES = [60, 64, 67, 70, 76, 48, 36, 79, 48, 55, 74, 77, 84, 100, 101, 102] # ,103]

PITCH = -12

input()
for note in NOTES:
    inst.send_event(EventNoteOn(note + PITCH, 100))

input()

for note in NOTES:
    inst.send_event(EventNoteOff(note + PITCH))

input()
synth.halt()
