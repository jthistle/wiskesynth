
from .event import EventType
from .note import Note


class Instrument:
    def __init__(self, parent, bank_num, preset_num):
        self.parent = parent
        for preset in self.sfont.presets:
            if preset.bank == bank_num and preset.preset_num == preset_num:
                self.preset = preset
                break

        self.notes = []

    @property
    def sfont(self):
        return self.parent.sfont

    def send_event(self, event):
        if event.type == EventType.NOTE_ON:
            instrument = self.preset.get_instrument(event.note, event.velocity, self.sfont.instruments)
            sample = instrument.get_sample(event.note, event.velocity, self.sfont.samples)
            gens, mods = self.preset.get_gens_and_mods(event.note, event.velocity, instrument)
            self.notes.append(Note(event.note, event.velocity, sample, gens, mods))