#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

###
# Project          : SubLime
# FileName         : core.py
# -----------------------------------------------------------------------------
# Author           : sham
# E-Mail           : mauricesham@gmail.com
# -----------------------------------------------------------------------------
# Creation date    : 17/01/2014
##

import logging
import os
import shutil
import guessit
import enzyme
import glob
import uuid

from babelfish import Language
from babelfish import Error as BabelfishError
from babelfish.exceptions import LanguageConvertError

from sublime.file import FileMagic
from sublime.file import FileMagicError

# Logger
LOG = logging.getLogger("sublime.core")


# -----------------------------------------------------------------------------
#
# Video class
#
# -----------------------------------------------------------------------------
class Video(object):

    """ Video class. """

    # List of video extensions
    EXTENSIONS = (
        '.3g2', '.3gp', '.3gp2', '.3gpp', '.60d', '.ajp', '.asf',
        '.asx', '.avchd', '.avi', '.bik', '.bix', '.box', '.cam',
        '.dat', '.divx', '.dmf', '.dv', '.dvr-ms', '.evo', '.flc',
        '.fli', '.flic', '.flv', '.flx', '.gvi', '.gvp', '.h264',
        '.m1v', '.m2p', '.m2ts', '.m2v', '.m4e', '.m4v', '.mjp',
        '.mjpeg', '.mjpg', '.mkv', '.moov', '.mov', '.movhd',
        '.movie', '.movx', '.mp4', '.mpe', '.mpeg', '.mpg', '.mpv',
        '.mpv2', '.mxf', '.nsv', '.nut', '.ogg', '.ogm', '.omf',
        '.ps', '.qt', '.ram', '.rm', '.rmvb', '.swf', '.ts', '.vfw',
        '.vid', '.video', '.viv', '.vivo', '.vob', '.vro', '.wm',
        '.wmv', '.wmx', '.wrap', '.wvx', '.wx', '.x264', '.xvid'
    )

    UNDERSCORE = True

    # FileMagic to determine file type
    FILE_MAGIC = FileMagic(EXTENSIONS)

    def __init__(self, video_filepath):
        """ Initializes instance. """
        self.id = uuid.uuid4()
        self.filename = os.path.abspath(video_filepath)
        self.size = str(os.path.getsize(self.filename))
        self.signature = None
        self.languages_to_download = []

    def rename(self):
        """ Rename movie to a cleaner name. """
        raise NotImplementedError("Please Implement this method")

    def _move(self, new_name):
        """ Move to a new name. """
        dir_name = os.path.dirname(self.filename)
        _, extension = os.path.splitext(os.path.basename(self.filename))

        new_filename = os.path.join(dir_name, new_name + extension)

        try:
            shutil.move(self.filename, new_filename)
        except Exception as error:
            LOG.error(
                "Cannot rename the file {}: {}".format(self.filename, error))
        else:
            self.filename = new_filename

    def has_subtitle(self, language):
        """ Returns true if the video has already
        a subtitle for a specific language. """
        has_subtitle = False

        # Look for embedded subtitle in mkv video
        if Video.is_mkv(self.signature):
            with open(self.filename, 'rb') as file_handler:
                mkv_video = enzyme.MKV(file_handler)

            for sub in mkv_video.subtitle_tracks:
                try:
                    if sub.language and \
                            Language.fromalpha3b(sub.language) == language:
                        has_subtitle = True
                        break
                    elif sub.name and \
                            Language.fromname(sub.name) == language:
                        has_subtitle = True
                        break
                except BabelfishError:
                    LOG.error(
                        "Embedded subtitle track"
                        "language {} is not a valid language"
                        .format(sub.language))

        # Look for external subtitle
        dir_name = os.path.dirname(self.filename)
        base_name, _ = os.path.splitext(os.path.basename(self.filename))

        # Select the most appropriate language code (alpha2)
        language_code = language.alpha3
        try:
            language_code = language.alpha2
        except LanguageConvertError:
            pass

        search_subtitle = os.path.join(
            dir_name, "{}.{}.*".format(base_name, language_code))
        existing_subtitles = [
            sub_file for sub_file in glob.glob(search_subtitle)
            if os.path.splitext(sub_file)[1] in Subtitle.EXTENSIONS
        ]

        if existing_subtitles:
            has_subtitle = True

        return has_subtitle

    @staticmethod
    def get_video_signature(video_filepath):
        """ Gets video file signature
            if a file given by its filepath is a video. """
        return Video.FILE_MAGIC.get_video_signature(video_filepath)

    @staticmethod
    def is_mkv(file_signature):
        """ Determines if a file signature is a MKV. """
        return Video.FILE_MAGIC.is_mkv(file_signature)

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return "<Video('{}', '{}', '{}', '{}')>".format(
            self.filename, self.id, self.size)


# -----------------------------------------------------------------------------
#
# Movie class
#
# -----------------------------------------------------------------------------
class Movie(Video):

    """ Movie class. """

    def __init__(self, video_filepath):
        """ Initializes instance. """
        Video.__init__(self, video_filepath)

        self.name = "UNKNOWN MOVIE"

    def rename(self):
        """ Rename movie to a cleaner name. """
        new_name = "{}".format(self.name)

        if Video.UNDERSCORE:
            new_name = new_name.replace(" ", "_")

        Video._move(self, new_name)

        return self.filename

    def __repr__(self):
        return "<Movie('{}')>".format(self.name)


# -----------------------------------------------------------------------------
#
# Episode class
#
# -----------------------------------------------------------------------------
class Episode(Video):

    """ Episode class. """

    RENAME_PATTERN = "{serie_name} S{season:02d}E{episode:02d} {episode_name}"

    def __init__(self, video_filepath):
        """ Initializes instance. """
        Video.__init__(self, video_filepath)

        self.name = "UNKNOWN SERIE"
        self.season = 0
        self.episode = 0
        self.episode_name = "UNKNOWN EPISODE"

    def rename(self):
        """ Rename movie to a cleaner name. """
        new_name = Episode.RENAME_PATTERN.format(
            serie_name=self.name,
            season=self.season,
            episode=self.episode,
            episode_name=self.episode_name
        )

        if Video.UNDERSCORE:
            new_name = new_name.replace(" ", "_")

        Video._move(self, new_name)

        return self.filename

    def __repr__(self):
        return "<Episode('{}', '{}', '{}', '{}')>".format(
            self.name, self.season, self.episode, self.episode_name)


# -----------------------------------------------------------------------------
#
# NamePattern class as Context Manager
#
# -----------------------------------------------------------------------------
class NamePattern(object):

    """ Pattern context manager used for renaming video files. """

    def __init__(self, pattern=None, underscore=True):
        self.default_pattern = Episode.RENAME_PATTERN
        self.pattern = pattern
        self.underscore = underscore

    def __enter__(self):
        if self.pattern:
            Episode.RENAME_PATTERN = self.pattern

        Video.UNDERSCORE = self.underscore

        return self.pattern

    def __exit__(self, type, value, traceback):
        Episode.RENAME_PATTERN = self.default_pattern
        Video.UNDERSCORE = True


# -----------------------------------------------------------------------------
#
# VideoFactory class
#
# -----------------------------------------------------------------------------
class VideoFactory(object):

    """ VideoFactory class which creates Video instances. """

    @staticmethod
    def make_from_filename(video_filepath):
        """ Returns a Movie or an Episode instance if it is possible,
        else returns a Video instance or None. """
        video = None

        if os.path.exists(video_filepath):
            try:
                video_signature = Video.get_video_signature(video_filepath)

                if video_signature:
                    guess = guessit.guess_movie_info(
                        video_filepath, info=['filename'])
                    if guess['type'] == 'movie':
                        video = Movie(video_filepath)
                    elif guess['type'] == 'episode':
                        video = Episode(video_filepath)
                    else:
                        video = Video(video_filepath)

                    video.signature = video_signature
            except FileMagicError:
                LOG.warning(
                    "This file was not recognized as a video file: {}".format(
                        video_filepath))
        else:
            LOG.error(
                "The following doesn't exists: {}".format(video_filepath))

        return video

    @staticmethod
    def make_from_type(video, video_type):
        """ Transforms a video into a Movie or Episode
        depending on video_type. """
        if not isinstance(video, (Movie, Episode)):
            new_video = video_type(video.filename)
            new_video.signature = video.signature
            new_video.languages_to_download = video.languages_to_download
        else:
            new_video = video

        return new_video


# -----------------------------------------------------------------------------
#
# Subtitle class
#
# -----------------------------------------------------------------------------
class Subtitle(object):

    """ Subtitle class manages subtitle files. """

    # List of subtitles extensions
    EXTENSIONS = (
        ".aqt", ".jss", ".sub", ".ttxt",
        ".pjs", ".psb", ".rt", ".smi",
        ".ssf", ".srt", ".gsub", ".ssa",
        ".ass", ".usf", ".txt"
    )

    def __init__(self, unique_id, language, video, rating=0, extension=None):
        """ Initializes instance. """
        self.id = unique_id
        self.language = language
        self.video = video
        self.rating = rating
        self.extension = extension

    @property
    def filepath(self):
        """ Get filepath of subtitle file we want to write. """
        dir_name = os.path.dirname(self.video.filename)
        base_name, _ = os.path.splitext(os.path.basename(self.video.filename))

        # Select the most appropriate language code (alpha2)
        language_code = self.language.alpha3
        try:
            language_code = self.language.alpha2
        except LanguageConvertError:
            pass

        filename = "{}.{}.{}".format(
            base_name, language_code, self.extension)

        return os.path.join(dir_name, filename)

    def write(self, data):
        """ Writes Subtitle on disk. """
        with open(self.filepath, 'wb') as out_file:
            out_file.write(data)

    def __eq__(self, other):
        return (self.language == other.language and self.video == other.video)

    def __lt__(self, other):
        return (self == other and self.rating < other.rating)

    def __gt__(self, other):
        return (self == other and self.rating > other.rating)

    def __repr__(self):
        return "<Subtitle('{}', '{}', '{}', '{}')>".format(
            self.id, self.language.alpha3, self.rating, self.extension)


# -----------------------------------------------------------------------------
#
# Exceptions
#
# -----------------------------------------------------------------------------
class VideoError(Exception):
    pass


class VideoSizeError(VideoError):

    """ Exception raised if the size of a movie file is too small.

    Attributes:
        video_filepath -- path of video file """

    def __init__(self, video_filepath):
        self.video_filepath = video_filepath

    def __str__(self):
        return "Size of movie file called {} is too small.".format(
            self.video_filepath)


class VideoHashCodeError(VideoError):

    """ Exception raised if there is an error during hash code generation.

    Attributes:
        video_filepath -- path of video file
        error -- error raised during hash code generation. """

    def __init__(self, video_filepath, error):
        self.video_filepath = video_filepath
        self.error = error

    def __str__(self):
        return (
            "Error during hash code generation for movie file called {}: {}."
            .format(self.video_filepath, self.error)
        )


# EOF
