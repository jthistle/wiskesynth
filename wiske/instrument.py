
from .event import EventType
from .note import Note

from .util.logger import logger


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
            if not sample:
                logger.warning("Could not find sample for note at key {}, vel {} in instrument {}".format(event.note, event.velocity, instrument.name))
                return

            gens, mods = self.preset.get_gens_and_mods(event.note, event.velocity, instrument)
            new_note = Note(self.parent.interface, event.note, event.velocity, sample, gens, mods)
            self.notes.append(new_note)
            new_note.play()
        elif event.type == EventType.NOTE_OFF:
            for i in range(len(self.notes) - 1, -1, -1):
                note = self.notes[i]
                if note.key != event.note:
                    continue
                note.stop()
                del self.notes[i]
