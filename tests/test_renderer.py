"""Offline regression tests using geometric fixtures, not private product photos."""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCRIPT = Path(__file__).resolve().parents[1] / 'product-spotlight-video/scripts/render.py'
SPEC = importlib.util.spec_from_file_location('spotlight_renderer', SCRIPT)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class TimelineTests(unittest.TestCase):
    def test_default_frame_boundaries(self):
        fps, count, states = renderer.schedule({'products': [{}, {}, {}]})
        self.assertEqual((fps, count), (30, 256))
        for index, expected in [(0, ()), (2, ()), (3, (0,)), (27, (0,)), (28, ()), (63, (1,)), (87, (1,)), (88, ()), (122, (2,)), (146, (2,)), (147, ()), (177, (0, 1, 2)), (255, (0, 1, 2))]:
            self.assertEqual(states[index], expected)

    def test_invalid_events_fail(self):
        for events in [
            [{'start': 0, 'end': 1, 'products': [3]}],
            [{'start': 0, 'end': 2, 'products': [0]}, {'start': 1, 'end': 3, 'products': [1]}],
            [{'start': 1, 'end': 0, 'products': [0]}],
        ]:
            with self.assertRaises(ValueError):
                renderer.schedule({'products': [{}, {}, {}], 'events': events})


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.exe = renderer.ffmpeg_path(os.environ.get('SPOTLIGHT_FFMPEG'))

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, size=(256, 176), single=False):
        width, height = size
        scene = Image.new('RGB', size, (28, 40, 50))
        drawing = ImageDraw.Draw(scene)
        products = []
        for i, color in enumerate([(220, 170, 120), (210, 200, 150), (160, 220, 190)]):
            x0, x1 = .12 + i*.27, .31 + i*.27
            box = [x0, .4, x1, .85]
            drawing.rectangle([renderer.xy(box[:2], width, height), renderer.xy(box[2:], width, height)], fill=color)
            products.append({'label': f'P{i+1}', 'box': box, 'label_position': [x0, .15], 'feather': 0})
        scene.save(self.root / 'scene.png')
        config = {'scene': 'scene.png', 'size': list(size), 'products': products[:1] if single else products}
        if single:
            config.update(duration=1.0, events=[{'start': .1, 'end': .4, 'products': [0]}, {'start': .6, 'end': 1.0, 'products': [0]}])
        path = self.root / 'scene.json'
        path.write_text(json.dumps(config))
        return path, config

    def execute(self, path, folder='out'):
        with contextlib.redirect_stdout(io.StringIO()):
            return renderer.render(path, self.root / folder, self.exe)

    def test_three_products_independent_and_video_frames(self):
        path, config = self.prepare()
        manifest = self.execute(path)
        out = self.root / 'out'
        dark = np.asarray(Image.open(out / 'dark.png').convert('RGB')).astype(float)
        bright = np.asarray(Image.open(out / 'bright.png').convert('RGB')).astype(float)
        for state in manifest['states']:
            pixels = np.asarray(Image.open(out / state['image']).convert('RGB')).astype(float)
            for i in range(3):
                x = round((.215 + i*.27)*256)
                patch = pixels[100:110, x-3:x+3]
                expected = bright[100:110, x-3:x+3] if i in state['products'] else dark[100:110, x-3:x+3]
                self.assertLess(np.abs(patch - expected).max(), 3, (state, i))
        decoded = subprocess.run([self.exe, '-v', 'error', '-i', str(out / 'product-spotlight.mp4'), '-f', 'rawvideo', '-pix_fmt', 'gray', 'pipe:1'], capture_output=True, check=True).stdout
        self.assertEqual(len(decoded), 256*176*256)
        frames = np.frombuffer(decoded, dtype=np.uint8).reshape(256,176,256)
        for start, cup in [(3,0), (63,1), (122,2)]:
            x = round((.215 + cup*.27)*256)
            self.assertGreater(frames[start,100:110,x-3:x+3].mean() - frames[start-1,100:110,x-3:x+3].mean(), 50)
        with wave.open(str(out / 'audio.wav')) as audio:
            self.assertAlmostEqual(audio.getnframes()/audio.getframerate(), 256/30, places=4)
            self.assertGreater(np.abs(np.frombuffer(audio.readframes(audio.getnframes()),dtype='<i2')).max(), 100)
        with self.assertRaises(ValueError):
            self.execute(path)

    def test_single_product_portrait_and_short_audio_padding(self):
        path, config = self.prepare((176,256), single=True)
        with wave.open(str(self.root / 'short.wav'), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(44100)
            audio.writeframes(np.zeros(4410,dtype='<i2').tobytes())
        config['audio'] = 'short.wav'
        path.write_text(json.dumps(config))
        manifest = self.execute(path)
        self.assertEqual(manifest['size'], [176,256])
        self.assertEqual(manifest['frames'],30)
        with wave.open(str(self.root / 'out/audio.wav')) as audio:
            self.assertEqual(audio.getnframes(),44100)

    def test_aspect_ratio_mismatch_is_rejected(self):
        path, config = self.prepare()
        config['size']=[176,256]
        path.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError,'aspect ratios'):
            self.execute(path)


if __name__ == '__main__':
    unittest.main()
