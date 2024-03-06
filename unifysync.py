from argparse import ArgumentParser
from random import choices
from shutil import which, rmtree
from subprocess import run
from string import ascii_letters, digits
from urllib.parse import unquote
from pathlib import Path
from time import sleep
from logging import basicConfig, DEBUG, INFO, info, error
from pySmartDL import SmartDL
from tempfile import gettempdir
from sys import exit


def generate_random_string(length: int) -> str:
    return str().join(choices(ascii_letters + digits, k=length))


def download_file(url: str, output_path: Path) -> None:
    if args.quiet or args.generate_logfile:
        progress_bar_status = False
    else:
        progress_bar_status = True

    obj = SmartDL(url, dest=output_path.as_posix(), progress_bar=progress_bar_status, fix_urls=True, threads=40)
    obj.start()


def merge_media_files(ffmpeg_path: Path, video_path: Path, audio_path: Path, output_path: Path) -> None:
    info(f'Merging "{video_path.as_posix()}" and "{audio_path.as_posix()}" into "{output_path.as_posix()}"...')
    ffmpeg_path = ffmpeg_path.as_posix()
    video_path = video_path.as_posix()
    audio_path = audio_path.as_posix()
    output_path = Path(output_path).resolve().as_posix()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_command = f'"{ffmpeg_path}" -i "{video_path}" -i "{audio_path}" -c copy -y -hide_banner -loglevel error "{output_path}"'

    try:
        info(f'Running FFmpeg command: {ffmpeg_command}')
        run(ffmpeg_command, shell=False, check=True)
    except Exception as e:
        error(f'An error occurred while merging the files: {e}')
        exit()

    info(f'Merged file saved to "{output_path}"')


def download_and_merge(video_url: str, audio_url: str, output_path: str) -> None:
    info('Initializing application...')
    info('Checking if FFmpeg is installed and in the system PATH...')
    user_ffmpeg_path = which('ffmpeg')

    if user_ffmpeg_path:
        ffmpeg_path = Path(user_ffmpeg_path).resolve()
        info(f'Using FFmpeg located at "{ffmpeg_path.as_posix()}"...')
    else:
        error('FFmpeg is not installed or not in the system PATH. Please install FFmpeg and try again.')
        exit()

    info(f'Using temporary directory "{temp_dir.as_posix()}"...')

    count_to_attempt = 1

    video_url = unquote(video_url)
    audio_url = unquote(audio_url)

    if not output_path:
        output_path = Path.cwd()
    else:
        if not str(output_path).strip():
            output_path = Path.cwd()
        else:
            output_path = Path(output_path)

    if output_path.is_dir() or not output_path.suffix:
        output_path = Path(output_path, f'output_{temp_num}.mp4')
    else:
        output_path = output_path.resolve()

        real_suffix_string = output_path.suffix.replace('.', str()).strip()

        if not real_suffix_string:
            output_path = Path(output_path.as_posix().replace(output_path.suffix, '.mp4'))
        else:
            output_path = Path(output_path.as_posix().strip())

    output_path = Path(output_path).resolve()
    video_path = Path(temp_dir, f'.video_{temp_num}.mp4').resolve()
    audio_path = Path(temp_dir, f'.audio_{temp_num}.mp3').resolve()
    info(f'Application will download the video file to "{video_path.as_posix()}", the audio file to "{audio_path.as_posix()}", and merge them into "{output_path.as_posix()}"...')

    for url, path in ((video_url, video_path), (audio_url, audio_path)):
        info(f'Downloading "{url}..." to "{path.as_posix()}"...')
        download_file(url, path)

    def count_to(number: int, text: str) -> None:
        global count_to_attempt

        for i in range(number, 0, -1):
            info(text.format(count_to_attempt, i), extra={'end': '\r'})
            sleep(1)

        count_to_attempt += 1

    count_to_attempt = 1

    while not video_path.exists() or not audio_path.exists():
        count_to(8, 'merger-{} - Checking if the files have been downloaded in {} seconds...')

        if video_path.exists() and audio_path.exists():
            break

    merge_media_files(ffmpeg_path, video_path, audio_path, output_path)

    info('Cleaning the application temporary directory...')
    rmtree(temp_dir)


def parse_arguments():
    parser = ArgumentParser(description='Merge audio and video files into a single file.')
    parser.add_argument('-v', '--version',                          dest='version',                          action='version',                                                                        version='0.0.1')
    parser.add_argument('-vu', '--video-url',       required=True,  dest='video_url',        metavar='URL',                       help='URL of the video file')
    parser.add_argument('-au', '--audio-url',       required=True,  dest='audio_url',        metavar='URL',                       help='URL of the audio file')
    parser.add_argument('-o', '--output',           required=False, dest='output_path',      metavar='PATH',                      help='Output file path (including path, file name, and extension)')
    parser.add_argument('-l', '--generate-logfile', required=False, dest='generate_logfile',                 action='store_true', help='Enable logging to a file')
    parser.add_argument('-q', '--quiet',            required=False, dest='quiet',                            action='store_true', help='Silence terminal output')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_arguments()

    system_temp_dir = gettempdir()

    def gen_temp_info() -> tuple:
        _temp_num = generate_random_string(8)
        _temp_dir = Path(system_temp_dir, f'.temp-{_temp_num}').resolve()
        return _temp_num, _temp_dir

    temp_num, temp_dir = gen_temp_info()

    while temp_dir.exists():
        temp_num, temp_dir = gen_temp_info()

    temp_dir.mkdir()

    if args.generate_logfile:
        basicConfig(filename=f'runtime-{temp_num}.log', level=DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    elif not args.quiet:
        basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    download_and_merge(video_url=args.video_url, audio_url=args.audio_url, output_path=args.output_path)
