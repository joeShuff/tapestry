# Tapestry player: Pi setup

Replace `pi` and `card-pi` with your username and hostname throughout.

## Part 1: do now (no parts needed)

1. **Flash the OS.** Raspberry Pi Imager, Raspberry Pi OS Lite (64-bit). In the settings gear set hostname `card-pi`, a username and password, your Wi-Fi, and enable SSH.
2. **Connect.** `ssh pi@card-pi.local`, then `sudo apt update && sudo apt full-upgrade -y`.
3. **Install packages.** `sudo apt install -y mpv python3-venv python3-pip i2c-tools`
4. **Copy the player over.** From your computer: `scp tapestry.zip pi@card-pi.local:~`, then on the Pi `unzip tapestry.zip && cd tapestry/player`.
5. **Python environment.** `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
6. **Configure.** `cp config.example.toml config.toml` and set `server_url` to the machine running the Tapestry server (`http://<its-ip>:8080`). Check from the Pi: `curl http://<its-ip>:8080/api/v1/files`.
7. **Test with typed card IDs.** `.venv/bin/python -m tapestry_player --reader stdin`
   - Assign a card ID to some audio in the portal (use "Add card" and invent an ID like `04AABBCC`).
   - Type that ID and press Enter: the file downloads and plays.
   - Press Enter on an empty line: pauses. Type the same ID: resumes.
   - Type an ID you haven't assigned: the player logs "No audio", and the ID appears in the portal's Waiting tab.
   - No speaker yet? Set `audio_device = "null"` to test everything except sound, or plug in a USB sound card.
8. **Test offline.** Stop the Tapestry server, type a card you already played: it plays from the cache.

## Part 2: when the parts arrive

1. Power off, wire it per the diagrams, power on.
2. **Enable I2C and the amp.** `sudo raspi-config nonint do_i2c 0`, then add to `/boot/firmware/config.txt`:
   ```
   dtparam=i2c_arm_baudrate=10000
   dtoverlay=hifiberry-dac
   ```
   Reboot. (Overlay names occasionally change; check the current Pi docs if the amp isn't detected.)
3. **Check the reader.** `i2cdetect -y 1` should show `24`. No `24`? Recheck wiring and the PN532's I2C mode switches.
4. **Check audio.** `aplay -l` should list a `sndrpihifiberry` card. `speaker-test -c1 -t wav` should play speech from the speaker.
5. **Find the audio device name.** `mpv --audio-device=help`, then set `audio_device` in `config.toml` (e.g. `alsa/plughw:CARD=sndrpihifiberry`). For a USB sound card, use its entry from the same list.
6. **Install the NFC libraries.** `.venv/bin/pip install -r requirements-nfc.txt`
7. **Test the reader.** `.venv/bin/python -m tapestry_player.readers`. Tap cards and the figures; you should see `present` and `removed` events with each ID. Try through 3-5 mm of plastic to see the range you'll have in a case.
8. Set `reader = "pn532"` in `config.toml` and run `.venv/bin/python -m tapestry_player`.

## Part 3: run it on boot

```
sudo cp tapestry-player.service /etc/systemd/system/
sudo systemctl enable --now tapestry-player
journalctl -u tapestry-player -f
```
If your username isn't `pi`, edit `User=` and the paths in the service file first.

## Troubleshooting

| Symptom | Check |
|---|---|
| "Server unreachable" | `curl` the server from the Pi; firewall on the server machine; correct IP in `config.toml` |
| "mpv did not start" | `which mpv`; run `mpv --idle` manually to see errors |
| No sound | `audio_device` name; `speaker-test`; volume in `config.toml` |
| Reader misses taps | Slow I2C setting in `config.txt`; cards flat and centred on the antenna; try `tag_misses = 5` |
| Card plays from the start every time | Check `~/.local/share/tapestry/positions.json` is being written |
