#!/usr/bin/env python3
"""Render deterministic product spotlight videos from an agent-prepared scene."""
import argparse
import json
import math
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def ffmpeg_path(explicit=None):
    if explicit:
        return explicit
    found = shutil.which('ffmpeg')
    if found:
        return found
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(exe, args):
    subprocess.run([exe, '-y', '-hide_banner', '-loglevel', 'error', *args], check=True)


def font_path(explicit=None, bold=True):
    if explicit:
        if not Path(explicit).is_file():
            raise ValueError(f'Font not found: {explicit}')
        return explicit
    candidates = [
        'C:/Windows/Fonts/ARIALNB.TTF',
        '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf',
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    ]
    if not bold:
        candidates = [p.replace('ARIALNB.TTF', 'ARIALN.TTF').replace('-Bold.ttf', '.ttf').replace('Arial Narrow Bold.ttf', 'Arial Narrow.ttf').replace('Arial Bold.ttf', 'Arial.ttf') for p in candidates]
    return next((p for p in candidates if Path(p).is_file()), None)


def xy(point, width, height):
    if len(point) != 2 or not all(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 1 for v in point):
        raise ValueError('Coordinates must be normalized [x, y] values between 0 and 1.')
    return round(point[0] * (width - 1)), round(point[1] * (height - 1))


def schedule(config):
    count = len(config['products'])
    duration = config.get('duration', 8.533333333)
    fps = config.get('fps', 30)
    if not isinstance(fps, int) or not 1 <= fps <= 60:
        raise ValueError('fps must be an integer between 1 and 60.')
    if not math.isfinite(duration) or not 0 < duration <= 120:
        raise ValueError('duration must be between 0 and 120 seconds.')
    frames = round(duration * fps)
    if frames < 1:
        raise ValueError('duration must contain at least one frame.')
    events = config.get('events')
    if events is None:
        if count != 3:
            raise ValueError('Custom events are required when product count is not three.')
        events = [
            {'start': 0.1, 'end': 28 / 30, 'products': [0]},
            {'start': 2.1, 'end': 88 / 30, 'products': [1]},
            {'start': 122 / 30, 'end': 4.9, 'products': [2]},
            {'start': 5.9, 'end': duration, 'products': [0, 1, 2]},
        ]
    states = [()] * frames
    occupied = set()
    for event in events:
        start, end = event['start'], event['end']
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (start, end)) or not 0 <= start < end <= duration + 1e-6:
            raise ValueError('Each event must satisfy 0 <= start < end <= duration.')
        active = tuple(sorted(set(event['products'])))
        if not active or any(type(i) is not int or not 0 <= i < count for i in active):
            raise ValueError('Event products must contain valid zero-based product indices.')
        a, b = round(start * fps), min(round(end * fps), frames)
        if b <= a or occupied.intersection(range(a, b)):
            raise ValueError('Events must not overlap or collapse to zero frames.')
        occupied.update(range(a, b))
        states[a:b] = [active] * (b - a)
    return fps, frames, states


def make_click_audio(path, states, fps):
    """Original synthesized switches; no downloaded music or reference audio."""
    rate = 44100
    signal = np.zeros(round(len(states) / fps * rate), dtype=np.float64)
    rng = np.random.default_rng(731)
    for frame, state in enumerate(states):
        if frame == 0 or state == states[frame - 1]:
            continue
        start = round(frame / fps * rate)
        n = min(round(.085 * rate), len(signal) - start)
        t = np.arange(n) / rate
        click = .13 * rng.standard_normal(n) * np.exp(-t * 115)
        click += .18 * np.sin(2 * np.pi * 1700 * t) * np.exp(-t * 90)
        if state:
            click += .07 * np.sin(2 * np.pi * 440 * t) * np.exp(-t * 40)
        signal[start:start+n] += click
    pcm = (np.clip(signal, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        audio.writeframes(pcm.tobytes())


def render(config_path, output_dir, executable=None, overwrite=False):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    root = config_path.parent
    output = Path(output_dir).resolve()
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise ValueError('Output directory is not empty. Choose a new directory or pass --overwrite.')
    products = config['products']
    if not 1 <= len(products) <= 6:
        raise ValueError('Provide between one and six products.')
    width, height = config.get('size', [1480, 1020])
    if any(type(v) is not int or v < 64 or v > 3840 or v % 2 for v in (width, height)):
        raise ValueError('Size must contain even integer dimensions from 64 to 3840.')
    dark_level = config.get('dark_level', .25)
    if not 0 <= dark_level < 1:
        raise ValueError('dark_level must be between 0 (inclusive) and 1 (exclusive).')
    fps, frame_count, states = schedule(config)
    scene = (root / config['scene']).resolve()
    if not scene.is_file():
        raise ValueError(f'Scene not found: {scene}')
    with Image.open(scene) as source:
        if abs(source.width / source.height - width / height) > .03:
            raise ValueError('Scene and output aspect ratios differ. Prepare the scene at the intended ratio.')
    exe = ffmpeg_path(executable)
    title_font_file = font_path(str((root / config['font']).resolve()) if config.get('font') else None)
    detail_font_file = font_path(str((root / config['detail_font']).resolve()) if config.get('detail_font') else None, bold=False)
    output.mkdir(parents=True, exist_ok=True)
    bright, dark = output / 'bright.png', output / 'dark.png'
    run(exe, ['-i', str(scene), '-vf', f'scale={width}:{height}:flags=lanczos', '-frames:v', '1', str(bright)])
    run(exe, ['-i', str(bright), '-vf', f'lutrgb=r=val*{dark_level}:g=val*{dark_level}:b=val*{dark_level}', '-frames:v', '1', str(dark)])
    with tempfile.TemporaryDirectory(prefix='spotlight-') as tmp:
        temp = Path(tmp)
        masks, titles = [], []
        for i, product in enumerate(products):
            mask = Image.new('L', (width, height), 0)
            drawing = ImageDraw.Draw(mask)
            if 'polygon' in product:
                if len(product['polygon']) < 3:
                    raise ValueError('A mask polygon requires at least three points.')
                drawing.polygon([xy(p, width, height) for p in product['polygon']], fill=255)
            else:
                x0, y0, x1, y1 = product['box']
                if x0 >= x1 or y0 >= y1:
                    raise ValueError('Mask boxes must have increasing coordinates.')
                drawing.rectangle([xy([x0, y0], width, height), xy([x1, y1], width, height)], fill=255)
            feather = product.get('feather', .006) * min(width, height)
            if not 0 <= feather <= min(width, height) * .1:
                raise ValueError('feather must be between 0 and 0.1 of the shortest edge.')
            mask = mask.filter(ImageFilter.GaussianBlur(feather))
            mask_path = temp / f'mask-{i}.png'
            mask.convert('RGB').save(mask_path)
            masks.append(mask_path)
            overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            drawing = ImageDraw.Draw(overlay)
            text_size = max(10, round(product.get('font_size', .026) * height))
            details_size = max(8, round(product.get('detail_size', .019) * height))
            face = ImageFont.truetype(title_font_file, text_size) if title_font_file else ImageFont.load_default(size=text_size)
            small = ImageFont.truetype(detail_font_file, details_size) if detail_font_file else ImageFont.load_default(size=details_size)
            x, y = xy(product['label_position'], width, height)
            drawing.text((x, y), product.get('label', f'PRODUCT {i+1:02}'), font=face, fill=config.get('title_color', '#DAE045'))
            for j, line in enumerate(product.get('details', [])):
                drawing.text((x, y + round(text_size * 1.2) + j * round(details_size * 1.15)), line, font=small, fill=config.get('detail_color', '#9A9D57'))
            title_path = temp / f'title-{i}.png'
            overlay.save(title_path)
            titles.append(title_path)
        # Render one still per unique state. All photometric compositing happens in
        # FFmpeg's RGB planes: YUV masks would unintentionally brighten other products.
        state_frames = {}
        for number, active in enumerate(dict.fromkeys(states)):
            result = output / f'state-{number:02}.png'
            if not active:
                shutil.copyfile(dark, result)
            else:
                inputs = ['-i', str(dark), '-i', str(bright)]
                for i in active:
                    inputs += ['-i', str(masks[i]), '-i', str(titles[i])]
                filters = ['[0:v]format=gbrp[base]']
                if len(active) == 1:
                    filters.append('[1:v]format=gbrp[b0]')
                else:
                    filters.append('[1:v]format=gbrp,split=' + str(len(active)) + ''.join(f'[b{j}]' for j in range(len(active))))
                prev = 'base'
                for j, i in enumerate(active):
                    filters += [f'[{2+j*2}:v]format=gbrp[m{j}]',
                                f'[{prev}][b{j}][m{j}]maskedmerge[lit{j}]',
                                f'[lit{j}][{3+j*2}:v]overlay=format=rgb,format=gbrp[s{j}]']
                    prev = f's{j}'
                run(exe, [*inputs, '-filter_complex', ';'.join(filters), '-map', f'[{prev}]', '-frames:v', '1', str(result)])
            with Image.open(result) as image:
                state_frames[active] = image.convert('RGB').tobytes()
        duration = frame_count / fps
        audio_file = output / 'audio.wav'
        if config.get('audio'):
            audio_source = (root / config['audio']).resolve()
            if not audio_source.is_file():
                raise ValueError(f'Audio source not found: {audio_source}')
            offset = config.get('audio_start', 0)
            if not isinstance(offset, (int, float)) or not math.isfinite(offset) or offset < 0:
                raise ValueError('audio_start must be a nonnegative number.')
            run(exe, ['-ss', str(offset), '-i', str(audio_source), '-vn', '-af', 'apad', '-t', str(duration), '-ar', '44100', '-ac', '1', str(audio_file)])
        else:
            make_click_audio(audio_file, states, fps)
        video = output / 'product-spotlight.mp4'
        command = [exe, '-y', '-hide_banner', '-loglevel', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{width}x{height}', '-framerate', str(fps), '-i', 'pipe:0', '-i', str(audio_file), '-map', '0:v', '-map', '1:a', '-frames:v', str(frame_count), '-t', str(duration), '-c:v', 'libx264', '-preset', 'medium', '-crf', str(config.get('crf', 18)), '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(video)]
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
            try:
                for state in states:
                    process.stdin.write(state_frames[state])
                process.stdin.close()
                code = process.wait()
            except BaseException:
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
                process.wait()
                log.seek(0)
                error = log.read().decode(errors='replace')
                if process.returncode:
                    raise RuntimeError(error or 'FFmpeg encoding failed.') from None
                raise
            if code:
                log.seek(0)
                raise RuntimeError(log.read().decode(errors='replace'))
        run(exe, ['-i', str(video), '-f', 'null', '-'])
        manifest = {'video': video.name, 'size': [width, height], 'fps': fps, 'frames': frame_count, 'duration': duration, 'audio': 'provided' if config.get('audio') else 'original synthesized switches', 'font': title_font_file or 'Pillow fallback', 'states': [{'products': list(state), 'image': f'state-{n:02}.png'} for n, state in enumerate(dict.fromkeys(states))]}
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, help='Agent-prepared JSON scene configuration.')
    parser.add_argument('--output', required=True, help='New output directory.')
    parser.add_argument('--ffmpeg', help='Optional FFmpeg executable path.')
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        render(args.config, args.output, args.ffmpeg, args.overwrite)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError, RuntimeError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
