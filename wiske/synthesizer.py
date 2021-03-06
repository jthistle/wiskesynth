
from .sf2.soundfont import Soundfont
from .interface import AudioInterface, AudioConfig
from .instrument import Instrument

import sys

class Synthesizer:
    sfont = None
    preset = None

    def __init__(self):
        cfg = AudioConfig()
        cfg.period_size = 128
        self.interface = AudioInterface(cfg, max_latency=0.0025)

        # Experimental
        sys.setswitchinterval(0.1)

    def load_soundfont(self, path):
        self.sfont = Soundfont(path)

    def new_instrument(self, bank, number):
        return Instrument(self, bank, number)

    def halt(self):
        self.interface.halt()

    def __str__(self):
        return "Synthesizer, using soundfont:\n{}\nand preset {}".format(
            self.sfont, self.preset
        )
