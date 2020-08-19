
import time
from wiske import Synthesizer, EventNoteOn, EventNoteOff

NOTE = 50

synth = Synthesizer()

synth.load_soundfont("/home/james/Downloads/GeneralUserGS/GeneralUserGS.sf2")

for preset in synth.sfont.presets:
    inst = synth.new_instrument(preset.bank, preset.preset_num)
    print(inst.preset.user_name)
    inst.send_event(EventNoteOn(NOTE, 100))
    time.sleep(0.6)
    inst.send_event(EventNoteOff(NOTE))

synth.halt()
