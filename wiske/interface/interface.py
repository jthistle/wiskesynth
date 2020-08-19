
import math
import time
import struct
from threading import Thread, Lock
from multiprocessing import Process, Queue, Pipe, Manager

from ..util.logger import logger
from .alsa import run_alsa
from .buffer import AudioBuffer
from .message import MessageType

from itertools import islice


class AudioInterface:
    def __init__(self, config, max_latency=0.2, use_buffering=False):
        # Format by default is signed 16-bit LE
        self.cfg = config
        self.frame_size = 2     # bytes

        self.use_buffering = use_buffering
        self.target_latency = 0.01      # only valid with use_buffering = True
        self.init_buffer_samples = int(self.cfg.sample_rate * self.target_latency)
        self.max_latency = max_latency
        self.volume = 0.1       # should not be changed during playback unless appropriate changes are made
        self.period_size_words = self.cfg.period_size * self.cfg.channels

        self.buffers = {}
        self.raw_buffers = {}
        self.custom_collect_funcs = {}
        self.last = 0

        self.halted = False

        # Playback process
        # Queue size = max latency / length of period
        queue_size = int(self.max_latency / self.cfg.period_length)
        self.alsa_data_queue = Queue(maxsize=queue_size)

        # ALSA relay
        self.alsa_thread = Process(target=run_alsa, args=(self.cfg, self.alsa_data_queue))

        # Communication with AudioBuffers under playback process
        self.playback_thread = Thread(target=self.start_playback_thread)

        self.alsa_thread.start()
        self.playback_thread.start()

        logger.info("Audio interface: init with cfg: {}".format(self.cfg))
        logger.info("Audio interface: queue size is {} (max latency {:.5f}s)".format(queue_size, max_latency))

        # Run some zeros through the system to prevent underruns on initial playback
        blank = [0] * self.cfg.sample_rate
        self.play(blank, 1)
        time.sleep(1)

    def __do_extend(self, start_point, buf_id, buffer, buf_size, channel_ratio):
        chunk_size = self.init_buffer_samples * 2
        while start_point < buf_size:
            xtnd = 0
            for i in range(start_point, min(start_point + chunk_size, buf_size)):
                for j in range(channel_ratio):
                    self.raw_buffers[buf_id].append(buffer[i])
                    xtnd += 1
            self.buffers[payload[0]].size += buf_size
            start_point += chunk_size

    def play(self, buffer, channels = 2, loop = None, immortal = False):
        """
        Play a buffer, which should be given as a list of frames. bytes-like objects
        are also accepted. channels specifies the number of channels of the buffer to
        be played, and must be a power of two and >= 1, and must be <= the audio config
        number of channels for this interface. If `immortal` is specified, the buffer
        will not be deleted upon finishing, allowing you to extend it or restart it.
        This comes with the responsibility of making sure not all the memory is used up
        by immortal buffers.
        """
        assert not self.halted

        # buffer should be given as a list of frames where possible
        if type(buffer) == bytes:
            buffer = struct.unpack("<h", buffer)

        buf_size = len(buffer)
        start_point = buf_size if not self.use_buffering else min(self.init_buffer_samples, buf_size)
        channel_ratio = self.cfg.channels // channels

        # We create an initial buffer up to a start point determined by the target latency
        new_data = []
        for i in range(start_point):
            for j in range(channel_ratio):
                new_data.append(buffer[i])

        self.last += 1
        loop = None if loop is None else tuple([x * channel_ratio for x in loop])
        buf = AudioBuffer(self.last, len(new_data), immortal, loop)

        self.raw_buffers[self.last] = new_data
        self.buffers[self.last] = buf

        # Now the buffer has been added to the playback processor, we can start extending it
        # with chunks while the first bit of it is playing back. Hopefully we can outpace it.
        if self.use_buffering:
            self.__do_extend(start_point, self.last, buffer, buf_size, channel_ratio)

        return self.last

    def extend(self, buffer_id, buffer, channels = 2):
        assert not self.halted

        # buffer should be given as a list of frames where possible
        if type(buffer) == bytes:
            buffer = struct.unpack("<h", buffer)

        buf_size = len(buffer)
        channel_ratio = self.cfg.channels // channels

        self.__do_extend(0, buffer_id, buffer, buf_size, channel_ratio)

        return buffer_id

    def end_loop(self, buffer_id):
        self.buffers[buffer_id].end_loop()

    def add_custom_buffer(self, custom_buf, collect_func):
        self.last += 1
        custom_buf.id = self.last
        self.custom_collect_funcs[self.last] = collect_func

        self.buffers[self.last] = custom_buf
        return self.last

    def start_playback_thread(self):
        # Local vars for optimization
        VAL_LIMIT = (1 << 15) - 1   # globals are slow
        raw_bufs = self.raw_buffers
        collect_funcs = self.custom_collect_funcs
        req_size = self.period_size_words
        buffers = self.buffers
        put_to_queue = self.alsa_data_queue.put
        check_queue_full = self.alsa_data_queue.full
        packer = struct.Struct("<{}h".format(req_size))
        pack_data = packer.pack
        volume = self.volume
        while True:
            if self.halted:
                break

            # Take the time to delete a single buffer if we think we can get away
            # with it, in order to free up memory
            if check_queue_full():
                for buf_id in buffers:
                    buf = buffers[buf_id]
                    if buf.finished and not buf.immortal:
                        try:
                            del raw_bufs[buf_id]
                        except IndexError:
                            del collect_funcs[buf_id]
                        del buffers[buf_id]
                        break

            final_data = [0] * req_size
            for buf_id in buffers:
                buffer = buffers[buf_id]
                meta = buffer.get_request(req_size)

                if not meta[0]:   # is not custom
                    _, buf_id, offset, loop_start, loop_end = meta
                    uses_loop = loop_start != -1 and loop_end != -1
                    if not uses_loop:
                        i = 0
                        for x in islice(raw_bufs[buf_id], offset, offset + req_size):
                            final_data[i] += x
                            i += 1
                        continue

                    i = 0
                    resp[buf_id] = []
                    while i < req_size:
                        chunk_size = min(req_size - i, req_size, loop_end - offset)

                        for x in islice(raw_bufs[buf_id], offset, offset + chunk_size):
                            final_data[i] += x
                            i += 1

                        offset = loop_start
                else:
                    _, buf_id, *args = meta
                    i = 0
                    for x in collect_funcs[buf_id](req_size, *args):
                        final_data[i] += x
                        i += 1

            put_to_queue(
                pack_data(
                    *(int(max(-VAL_LIMIT, min(VAL_LIMIT, x * volume))) for x in final_data)
                )
            )

    def halt(self):
        self.halted = True
        self.playback_thread.join()
        self.alsa_thread.terminate()

        del self.raw_buffers
