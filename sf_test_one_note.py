
from wiske import Synthesizer, EventNoteOn, EventNoteOff

NOTE = 50

synth = Synthesizer()

# synth.load_soundfont("/home/james/Downloads/GeneralUserGS/GeneralUserGS.sf2")
synth.load_soundfont("/home/james/Documents/MuseScore3Development/SoundFonts/MuseScore_General_Lite-v0.1.5/MuseScore_General_Lite.sf2")

inst = synth.new_instrument(0, 48)

# print(synth.sfont.presets_list_user())
print("ready")

# Seems to be about the maximum possible notes at the moment
NOTE = 60

input()
inst.send_event(EventNoteOn(NOTE, 100))

input()
inst.send_event(EventNoteOff(NOTE))

input()
synth.halt()
