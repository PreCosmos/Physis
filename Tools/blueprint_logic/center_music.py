"""Kept for the station's rebuild script, which runs this file after all of its own logic scripts:
it runs every Center override of shared Blueprint graphs, in Tools/blueprint_logic/center_overrides.py
(music, level start, death, saving and loading, the station's last quest, the main menu's Continue).
    python3 Tools/blueprint_logic/center_music.py
"""
import pathlib
import runpy

runpy.run_path(str(pathlib.Path(__file__).with_name('center_overrides.py')), run_name='__main__')
