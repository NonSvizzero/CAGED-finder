import operator
import os
import unittest
from functools import reduce

from mingus.core import scales
from mingus.core.mt_exceptions import NoteFormatError

from src import ASSETS_DIR
from src.analyzer import SUPPORTED_SCALES, Parser
from src.guitar import Song, String, Form, Note


class TestGuitar(unittest.TestCase):
    TEST_ASSETS = os.path.join(ASSETS_DIR, "tests")

    @classmethod
    def setUpClass(cls):
        cls.parser = Parser()
        cls.song = Song(os.path.join(cls.TEST_ASSETS, "test.gp5"))

    def setUp(self):
        self.parser.reset()

    def test_data(self):
        data = {
            "album": 'album',
            "artist": 'artist',
            "year": '2018',
            "genre": 'Moderate',
            "title": 'name'
        }
        self.assertDictEqual(data, self.song.data)

    def test_bpm(self):
        self.assertEqual(120, self.song.tempo)

    def test_tuning(self):
        self.assertEqual("EADGBE", self.song.guitars[0].tuning)

    def test_notes(self):
        beat = self.song.guitars[0].measures[0].beats[0]
        # all strings are strummed on zero exactly once
        self.assertTrue(all(note.fret == 0 for note in beat.notes))

    def test_chords(self):
        chord = self.song.guitars[1].measures[0].beats[0].chord
        self.assertEqual('C', chord.name)

    def test_form_matching(self):
        self.parser.parse_track(self.song.guitars[2])
        g_ionian_e = self.parser.forms_db['G']['Ionian']['E']
        g_pentatonic_e = self.parser.forms_db['G']['MajorPentatonic']['E']
        self.assertTrue(len(self.parser.forms_result[g_ionian_e]) == 1)
        self.assertTrue(len(self.parser.forms_result[g_pentatonic_e]) == 0)

    def test_pause(self):
        self.parser.parse_track(self.song.guitars[3])
        g_ionian_e = self.parser.forms_db['G']['Ionian']['E']
        self.assertTrue(len(self.parser.forms_result[g_ionian_e]) == 2)


class TestNote(unittest.TestCase):
    def test_ordering(self):
        high_e = Note(6, 0, 'E')
        low_e_1 = Note(1, 0, 'E')
        low_e_2 = Note(1, 0, 'E')
        self.assertLess(high_e, low_e_1)
        self.assertEqual(low_e_1, low_e_2)


class TestForm(unittest.TestCase):
    STRINGS = tuple(String(i, note) for i, note in enumerate('EBGDAE', start=1))

    def test_d_locrian(self):
        d_locrian = {
            1: [6, 8, 9],
            2: [6, 8, 9],
            3: [5, 6, 8],
            4: [5, 6, 8],
            5: [6, 8],
            6: [6, 8, 9]
        }
        self.match_scale(d_locrian, 'G', scales.Locrian, 'D')

    def test_a_locrian(self):
        a_locrian = {
            1: [11, 13],
            2: [11, 13, 14],
            3: [10, 12, 13],
            4: [10, 11, 13],
            5: [10, 11, 13],
            6: [11, 13]
        }
        self.match_scale(a_locrian, 'G', scales.Locrian, 'A')

    def match_scale(self, expected, key, scale, form):
        expected = tuple(self.STRINGS[string - 1].notes[fret] for string, frets in reversed(list(expected.items()))
                         for fret in frets)
        form = Form.calculate_form(key, scale, form)
        self.assertTupleEqual(expected, form.notes)

    def test_sum(self):
        """By chaining two close pentatonics we should get 3 notes per string"""
        scale = scales.MinorPentatonic
        key = 'G'
        f1 = Form.calculate_form(key, scale, 'C')
        f2 = Form.calculate_form(key, scale, 'A')
        f3 = f1 + f2
        for string in range(1, 7):
            self.assertEqual(3, len([note for note in f3.notes if note.string == string]))

    def test_caged_scales(self):
        """By combining the forms together we should get all the scale notes on each string"""
        keys = ('G',)
        for scale in SUPPORTED_SCALES:
            for key in keys:
                try:
                    scale_notes = set(scale(key).ascending()[:-1])
                except NoteFormatError:
                    continue
                s = reduce(operator.add, (Form.calculate_form(key, scale, form) for form in 'CAGED'))
                for string in self.STRINGS:
                    form_string_notes = set(note for note in s.notes if note.string == string.index)
                    self.assertTrue(form_string_notes.issubset(string.get_notes(scale_notes)))
