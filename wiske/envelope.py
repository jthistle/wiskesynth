
# Not an enum for performance reasons
class EnvelopeStage:
    DELAY = 0
    ATTACK = 1
    HOLD = 2
    DECAY = 3
    SUSTAIN = 4
    RELEASE = 5
    FINISHED = 6


class Envelope:
    def __init__(self, delay, attack, hold, decay, sustain, release):
        self.phases = [delay, attack, hold, decay, sustain, release, -1]

        self.current_phase = EnvelopeStage.DELAY
        self.position = 0
        self.start_val = 0
        self.current_val = 0
        self.target_val = 0
        self.total_time = self.phases[0]
        self.force_release = False

    def get_init_vals(self):
        return self.current_phase, self.position, self.start_val, self.current_val, self.target_val, self.total_time

    def update_vals(self, vals):
        if not self.force_release:
            self.current_phase, self.position, self.start_val, self.current_val, self.target_val, self.total_time = vals
        else:
            # Make sure we stay in release phase if it has been activated during a collection.
            _, self.position, self.start_val, self.current_val, self.target_val, self.total_time = vals
            self.force_release = False

    def next_phase(self):
        self.position = 0
        self.current_phase += 1
        self.total_time = self.phases[self.current_phase]      # Invalid if SUSTAIN or FINISHED

        if self.current_phase == EnvelopeStage.SUSTAIN:
            self.start_val = self.target_val
            self.current_val = self.target_val  # This will be the sustain value
        elif self.current_phase == EnvelopeStage.FINISHED:
            self.start_val = 0
            self.current_val = 0
            self.target_val = 0
        elif self.current_phase == EnvelopeStage.ATTACK:
            self.start_val = 0
            self.current_val = 0
            self.target_val = 1
        elif self.current_phase == EnvelopeStage.HOLD:
            self.start_val = 1
            self.current_val = 1
            self.target_val = 1
        elif self.current_phase == EnvelopeStage.DECAY:
            self.start_val = 1
            self.current_val = 1
            self.target_val = self.phases[EnvelopeStage.SUSTAIN]
        # EnvelopeStage.RELEASE is managed in `release`

        return self.start_val, self.target_val, self.total_time, self.current_phase

    @property
    def finished(self):
        return self.current_phase == EnvelopeStage.FINISHED

    def release(self):
        self.current_phase = EnvelopeStage.RELEASE
        self.position = 0
        self.start_val = self.current_val
        self.target_val = 0
        self.total_time = self.phases[self.current_phase]
        self.force_release = True
