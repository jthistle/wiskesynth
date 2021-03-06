
from math import ceil, pi, log10
import struct
import time

from .repitch import cents_to_ratio
from .sf2.definitions import SFGenerator, LoopType, SFGeneralController, SFModPolarity, SFModDirection, SFTransform, SFModType
from .interface import CustomBuffer
from .sf2.convertors import timecents_to_secs, decibels_to_atten, cents_to_hertz
from .envelope import Envelope
from .util.logger import logger


COARSE_SIZE = 2 ** 15
BASE_SAMPLE_RATE = 44100
SINGLE_SAMPLE_LEN = 1 / BASE_SAMPLE_RATE


class Note:
    def __init__(self, inter, key, on_vel, sample, gens, mods):
        self.inter = inter
        self.sample = sample
        self.key = key
        self.on_vel = on_vel
        self.init_gens = gens
        self.reset_gens_to_init()
        self.mods = mods

        self.playback = None
        self.position = 0

        # SoundFont spec 2.01, 8.1.2
        # SFGenerator.overridingRootKey:
        # "This parameter represents the MIDI key number at which the sample is to be played back
        #  at its original sample rate.  If not present, or if present with a value of -1, then
        #  the sample header parameter Original Key is used in its place.  If it is present in the
        #  range 0-127, then the indicated key number will cause the sample to be played back at
        #  its sample header Sample Rate"
        original_key = self.sample.pitch if self.gens[SFGenerator.overridingRootKey] == -1 else self.gens[SFGenerator.overridingRootKey]
        self.hard_pitch_diff = (self.key - original_key) * 100 + self.sample.pitch_correction
        self.hard_pitch_diff += self.gens[SFGenerator.coarseTune] * 100 + self.gens[SFGenerator.fineTune]

        sample_ratio = self.sample.sample_rate / BASE_SAMPLE_RATE
        self.total_ratio = sample_ratio * cents_to_ratio(self.hard_pitch_diff)

        offset_s = self.gens[SFGenerator.startAddrsOffset] + self.gens[SFGenerator.startAddrsCoarseOffset] * COARSE_SIZE
        offset_e = self.gens[SFGenerator.endAddrsOffset] + self.gens[SFGenerator.endAddrsCoarseOffset] * COARSE_SIZE

        loop_offset_s = self.gens[SFGenerator.startloopAddrsOffset] + self.gens[SFGenerator.startloopAddrsCoarseOffset] * COARSE_SIZE
        loop_offset_e = self.gens[SFGenerator.endloopAddrsOffset] + self.gens[SFGenerator.endloopAddrsCoarseOffset] * COARSE_SIZE
        loop_offset_s -= offset_s
        loop_offset_e -= offset_s

        self.sample_data = struct.unpack(
            "<{}h".format(self.get_data_size(sample.data, offset_s, offset_e) // 2),
            self.frame_sample_data(sample.data, offset_s, offset_e)
        )
        self.sample_size = len(self.sample_data)

        self.loop = None
        if self.gens[SFGenerator.sampleModes].loop_type in (LoopType.CONT_LOOP, LoopType.KEY_LOOP):
            self.loop = [
                self.sample.loop[0] + loop_offset_s,
                self.sample.loop[1] + loop_offset_e,
            ]

        self.vol_env = Envelope(
            timecents_to_secs(self.gens[SFGenerator.delayVolEnv]),
            timecents_to_secs(self.gens[SFGenerator.attackVolEnv]),
            timecents_to_secs(self.gens[SFGenerator.holdVolEnv]),
            timecents_to_secs(self.gens[SFGenerator.decayVolEnv]),
            decibels_to_atten(self.gens[SFGenerator.sustainVolEnv] / 10),   # sus uses cB = 1/10 dB
            timecents_to_secs(self.gens[SFGenerator.releaseVolEnv]),
        )

        self.channel_ratio = 2      # TODO do this properly
        self.single_sample_len = SINGLE_SAMPLE_LEN

        # LOW PASS cutoff
        self.recalculate_cutoff()
        self.last_val = 0

        # Attenuation
        self.recalculate_atten()

        # Optional debug:
        # print("gens")
        # for g in self.gens:
        #     print(">",g,self.gens[g])

        print("\n\nmods")
        for m in self.mods:
            print(">",m)

        # print("\nsample:", self.sample)

        self.last_mod_inputs = {
            SFGeneralController.noController: 0,
            SFGeneralController.noteOnKeyNum: key,
            SFGeneralController.noteOnVel: on_vel,
            SFGeneralController.polyPressure: 127,  # todo should be on_vel?
            SFGeneralController.channelPressure: 127,   # todo should be on_vel?
        }

        self.cached_modulator_values_raw = {}
        for i in range(len(self.mods)):
            self.recalculate_modulator(i)
        self.update_mod_destinations()

    def update_mod_input(self, mod_controller, amount):
        self.last_mod_inputs[mod_controller] = amount
        for i in range(self.mods):
            mod = self.mods[i]
            if mod.src.controller == mod_controller or mod.amt_src.controller == mod_controller:
                self.recalculate_modulator(i)
        self.update_mod_destinations()

    def recalculate_modulator(self, index):
        # Default to MIDI 127 for no real reason
        DEFAULT_MIDI_VAL = 127
        mod = self.mods[index]
        primary = mod.src
        primary_val = self.last_mod_inputs.get(primary.controller, DEFAULT_MIDI_VAL)
        mapped_primary = self.map_midi(primary_val, primary)
        secondary = mod.amt_src
        mapped_secondary = None
        secondary_val = None    # debug
        if secondary.controller == SFGeneralController.noController:
            mapped_secondary = 1
        else:
            secondary_val = self.last_mod_inputs.get(secondary.controller, DEFAULT_MIDI_VAL)
            mapped_secondary = self.map_midi(secondary_val, secondary)

        pre_transform = mapped_primary * mapped_secondary * mod.amount

        post_transform = None
        if mod.trans == SFTransform.linear:
            post_transform = pre_transform
        else:
            post_transform = abs(pre_transform)

        DO_PRINT_DEBUG = False

        if DO_PRINT_DEBUG:
            print("""
Primary
{p_val} from {p_src}
|
|     norm:     total sum  transformed    summing node
`-> [ {p_norm:.5f} ] -->▷{sum:.3f}->[ {transform:.3f} ] -> {node}  ({db:.6f}atn., {hz:.2f}Hz)
                 |
               {s_sum:.3f}  (amt. product)
                 |
                 /\ <-- {amount}  (amount)
                 |
      norm:  [ {s_norm:.5f} ]
                 |
                 |     Secondary
                 \.-- {s_val} from {s_src}
""".format(p_src=primary, p_val=primary_val, p_norm=mapped_primary, s_val=secondary_val, s_src=secondary, s_norm=mapped_secondary, amount=mod.amount,
            s_sum=mod.amount*mapped_secondary, sum=pre_transform, transform=post_transform, node=mod.dest,
            db=(decibels_to_atten(post_transform / 10) if 1 >= decibels_to_atten(post_transform / 10) >= 0 else -1), hz=cents_to_hertz(post_transform)))

        self.cached_modulator_values_raw[index] = post_transform

    def map_midi(self, val, sfmodulator):
        map_func = None
        if sfmodulator.type == SFModType.concave:
            map_func = self.map_concave
        elif sfmodulator.type == SFModType.convex:
            map_func = self.map_convex
        else:
            map_func = self.map_linear

        if sfmodulator.polarity == SFModPolarity.unipolar:
            return map_func(val / 128, sfmodulator.direction)
        else:
            if val <= 64:
                return -map_func((64 - val) / 64, sfmodulator.direction)
            else:
                return map_func((val - 64) / 64, sfmodulator.direction)

    # All map_* functions and base_conx expect val to be in the range (0, 1)
    def map_linear(self, val, direction):
        if direction == SFModDirection.negative:
            return 1 - val
        else:
            return val

    def map_convex(self, val, direction):
        if direction == SFModDirection.negative:
            return self.base_conx_function(1 - val)
        else:
            return self.base_conx_function(val)

    def map_concave(self, val, direction):
        if direction == SFModDirection.negative:
            return 1 - self.base_conx_function(val)
        else:
            return 1 - self.base_conx_function(1 - val)

    def base_conx_function(self, val):
        return log10(9 * val + 1)

    def update_mod_destinations(self):
        self.reset_gens_to_init()
        for i in range(len(self.mods)):
            mod = self.mods[i]

            if mod.dest == SFGenerator.initialFilterFc:
                self.gens[mod.dest] += cents_to_hertz(self.cached_modulator_values_raw[i])
                self.recalculate_cutoff()
            elif mod.dest == SFGenerator.initialAttenuation:
                print("adding atten {:.2f}cB to {:.2f}cB from mod {}".format(self.cached_modulator_values_raw[i], self.gens[mod.dest], i))
                self.gens[mod.dest] += self.cached_modulator_values_raw[i]
                self.recalculate_atten()
            else:
                pass # print("Unhandled dest:", mod.dest)
            # TODO a lot of stuff here

    def reset_gens_to_init(self):
        self.gens = {}
        for gen in self.init_gens:    # make shallow copy
            self.gens[gen] = self.init_gens[gen]

    def recalculate_cutoff(self):
        print("filter is", cents_to_hertz(self.gens[SFGenerator.initialFilterFc]))
        self.cutoff_time_const = 1 / (2 * pi * cents_to_hertz(self.gens[SFGenerator.initialFilterFc]))
        self.cutoff_alpha = SINGLE_SAMPLE_LEN / (SINGLE_SAMPLE_LEN + self.cutoff_time_const)

    def recalculate_atten(self):
        self.atten = decibels_to_atten(self.gens[SFGenerator.initialAttenuation] / 10)
        print("calc atten = {:.5f} from {:.2f}cB".format(self.atten, self.gens[SFGenerator.initialAttenuation]))
        # self.atten = 1

    def frame_sample_data(self, data, offset_s, offset_e):
        if offset_e == 0:
            return data[offset_s:]
        elif offset_e > 0:  # hack - todo handle this properly
            return data[offset_s:]
        elif offset_e < 0:
            return data[offset_s:offset_e]

    def get_data_size(self, data, offset_s, offset_e):
        if offset_e == 0:
            return len(data) - offset_s
        elif offset_e > 0:  # hack - todo handle this properly again
            return len(data) - offset_s
        elif offset_e < 0:
            return len(data) - offset_s + offset_e

    def play(self):
        if not self.sample.is_mono:
            print("Stereo samples are not supported yet")
            return

        self.playback = self.inter.add_custom_buffer(CustomBuffer(self.loop is not None), self.collect)

    def stop(self):
        self.vol_env.release()

    def collect(self, size, looping):
        """
        This function is extremely time sensitive, especially inside the while loop.
        Anything goes in terms of optimization. Even a tiny change can make a significant
        difference. Maintainability and clean code is secondary to performance here.
        """
        if self.vol_env.finished:
            self.inter.end_loop(self.playback)  # TODO thread this?
            # also, this no longer actually sets the buffer to 'finished'. Fix this.
            return

        channel_ratio = self.channel_ratio
        rate = self.total_ratio

        count = 0
        offset = ceil(rate)
        end = self.sample_size - offset

        # Whole load of local variables for optimization
        time_diff = self.single_sample_len
        loop = self.loop
        data = self.sample_data
        position = self.position
        vol_env = self.vol_env
        ve_phase, ve_position, ve_start_val, ve_current_val, ve_target_val, ve_total_time = vol_env.get_init_vals()

        two_ratio = channel_ratio == 2

        loop_s = loop[0]
        loop_e = loop[1]

        to_int = int   # this cuts a tiny sliver of time off the total running time

        # last_raw = self.last_val_raw
        last = self.last_val
        cutoff_alpha = self.cutoff_alpha
        reverse_cutoff_alpha = 1 - cutoff_alpha
        atten = self.atten
        while (looping or position < end) and count < size:
            i = to_int(position)
            frac = position - i
            s1 = data[i]
            # If adding the offset overshoots the end of the sample loop, make sure that we wrap back arround
            # to the start of the loop again. Enjoy the horrible conditional.
            s2 = data[i + offset if not looping or i + offset < loop_e else loop_s + (i + offset - loop_e)]
            val = (s1 + (s2 - s1) * frac) * ve_current_val * atten

            with_filter = cutoff_alpha * val + reverse_cutoff_alpha * last
            last = with_filter

            yield with_filter
            if two_ratio:
                yield with_filter
            count += channel_ratio

            position += rate
            if looping and position > loop_e:
                position = loop_s + (position - loop_e)

            if ve_phase not in (4, 6): # sustain, finished
                ve_position += time_diff
                if ve_position >= ve_total_time:
                    ve_start_val, ve_target_val, ve_total_time, ve_phase = vol_env.next_phase()
                    ve_current_val = ve_start_val
                    ve_position = 0
                else:
                    ve_current_val = ve_start_val + (ve_target_val - ve_start_val) * (ve_position / ve_total_time)

        self.position = position
        self.last_val = last

        vol_env.update_vals((ve_phase, ve_position, ve_start_val, ve_current_val, ve_target_val, ve_total_time))
