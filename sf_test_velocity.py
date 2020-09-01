
from wiske import Synthesizer, EventNoteOn, EventNoteOff

NOTE = 50

synth = Synthesizer()

synth.load_soundfont("/home/james/Downloads/GeneralUserGS/GeneralUserGS.sf2")
# synth.load_soundfont("/home/james/Documents/MuseScore3Development/SoundFonts/MuseScore_General_Lite-v0.1.5/MuseScore_General_Lite.sf2")

inst = synth.new_instrument(0, 0)

# print(synth.sfont.presets_list_user())
print("ready")

while True:
    try:
        vel = int(input("vel> "))
    except:
        break
    inst.send_event(EventNoteOn(NOTE, vel))
    input()
    inst.send_event(EventNoteOff(NOTE))

inst.send_event(EventNoteOff(NOTE))

input()
synth.halt()
