# Podaudrec - A simple, intuitive GUI for recording voice locally.
<img align="left" width="100" height="100" src="logo/cassette-2672633.png">

A simple Python based audio recorder - for local, non-exclusive audio recording. Repo based off of [Sounddevice's Audio Recorder GUI Example, with a QT spin](https://github.com/spatialaudio/python-sounddevice/blob/master/examples/rec_gui.py).

This project tries to have a localised audio recording for guests who are somewhat technically savy, and avoids the route of Squadcast.fm or Riverside.fm which, for a start, costs some money as an upfront payment and secondly stores the recordings on their own cloud, which is a red flag in corporate settings where recordings for podcasts have to be internalised.

Hence, since your guest is a little technically adept, she/he can follow a bunch of steps and have a very simple GUI to record locally, therefore improving the overall quality of the podcast.

<hr>

### Building an executable
1. Pip install "PyInstaller"
2. Then do something similar to the one below
```bash
cd myfolder
conda create -n exe python=3
activate exe
pip install pandas pyinstaller pypiwin32
echo hiddenimports = ['pandas._libs.tslibs.timedeltas'] > %CONDA_PREFIX%\Lib\site-packages\PyInstaller\hooks\hook-pandas.py
pyinstaller -F mycode.py
```
3. Distribute the executeable
4. Please note, remeber to change the "Upload to Drive" location to fit your needs