
import math
# import alsaaudio as aa
import time
import struct
from threading import Thread, Lock
from multiprocessing import Process, Queue, Pipe, Manager

from util.logger import logger
from .processor import run_processor
from .alsa import run_alsa
from .buffer import AudioBuffer
from .message import MessageType


class AudioInterface:
    def __init__(self, config, max_latency=0.2, use_buffering=False):
        # Format by default is signed 16-bit LE
        self.cfg = config
        self.frame_size = 2     # bytes

        self.use_buffering = use_buffering
        self.target_latency = 0.01      # only valid with use_buffering = True
        self.init_buffer_samples = int(self.cfg.sample_rate * self.target_latency)
        self.max_latency = max_latency

        self.buffer_pipes = []
        self.raw_buffers = {}
        self.last = 0

        # Playback process
        # Queue size = max latency / length of period
        queue_size = int(self.max_latency / self.cfg.period_length)
        self.playback_pipe, playback_rec = Pipe()
        alsa_data_queue = Queue(maxsize=queue_size)
        self.playback_thread = Process(target=run_processor, args=(self.cfg.period_size, playback_rec, alsa_data_queue))

        # ALSA relay
        self.alsa_thread = Process(target=run_alsa, args=(self.cfg, alsa_data_queue))

        # Communication with AudioBuffers under playback process
        self.read_buffers_thread = Thread(target=self.start_read_buffers_thread)

        self.playback_thread.start()
        self.alsa_thread.start()
        self.read_buffers_thread.start()

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
            self.playback_pipe.send((MessageType.EXTEND_BUFFER, (buf_id, xtnd)))
            start_point += chunk_size

    def play(self, buffer, channels = 2):
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
        buf = AudioBuffer(self.last, len(new_data))
        self.raw_buffers[self.last] = new_data
        self.playback_pipe.send((MessageType.NEW_BUFFER, buf))

        # Now the buffer has been added to the playback processor, we can start extending it
        # with chunks while the first bit of it is playing back. Hopefully we can outpace it.
        if self.use_buffering:
            self.__do_extend(start_point, self.last, buffer, buf_size, channel_ratio)

        return self.last

    def extend(self, buffer_id, buffer, channels = 2):
        # buffer should be given as a list of frames where possible
        if type(buffer) == bytes:
            buffer = struct.unpack("<h", buffer)

        buf_size = len(buffer)
        channel_ratio = self.cfg.channels // channels

        self.__do_extend(0, buffer_id, buffer, buf_size, channel_ratio)

        return buffer_id

    def start_read_buffers_thread(self):
        while True:
            self.playback_pipe.poll(timeout=None)
            reqs = self.playback_pipe.recv()

            resp = {}
            for buf_id, offset, size in reqs:
                resp[buf_id] = self.raw_buffers[buf_id][offset:offset + size]

            self.playback_pipe.send((MessageType.REQUEST_REPONSES, resp))
