
from wiske import Synthesizer, EventNoteOn, EventNoteOff

synth = Synthesizer()

synth.load_soundfont("/home/james/Downloads/GeneralUserGS/GeneralUserGS.sf2")

inst = synth.new_instrument(0, 40)

print("ready")

notes = []

offset = 20
for i in range(1000):
    x = input("{}> ".format(i))
    if x.lower().strip() == "end":
        break
    notes.append(i + offset)
    inst.send_event(EventNoteOn(i + offset, 100))
    print(i + offset)

    if i % 80 == 0 and i > 0:
        offset += -80

for note in notes:
    inst.send_event(EventNoteOff(note))

input()
synth.halt()
