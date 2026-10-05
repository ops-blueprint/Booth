# Booth

A voiceover studio that runs on your Mac. No subscription, no account, no internet needed after setup, and it never costs anything per word.

## Start it

Double-click **Start Booth.command**. A Terminal window opens (keep it open) and the studio opens in your browser at http://127.0.0.1:7863. Close the Terminal window to stop it.

The first time on a new Mac it runs `setup.sh`, which downloads about 2.5 GB of free models. On this Mac everything is already installed.

## Making a voiceover

1. Paste your script on the **Script** page.
2. Pick a voice. Michael (American) and George (British) are good documentary narrators. Or use your own cloned voice.
3. Press **Check pronunciation**. It lists acronyms, names and rare words. Tap any of them to hear it. If one sounds wrong, press Fix, type how it sounds ("win" for Nguyen), and it stays fixed for every future script.
4. Press **Generate voiceover**.
5. Download the **WAV** or **MP3** plus an **SRT subtitle file** that is already timed to the audio. Drop both into your editor.

If one line sounds off, edit it or press redo on that line. Only that line is regenerated.

### Script shortcuts

| Write this | What happens |
|---|---|
| a blank line | a natural paragraph pause |
| `[pause 1.5]` | a 1.5 second pause |
| `[GIF](jif)` | says the word the way you spell it in brackets |
| `[Nguyen](/wˈɪn/)` | exact phonemes (IPA), for built-in voices |
| `# Part 2` | headings are not read |
| `[B-ROLL: city at night]` | stage directions in square brackets are not read |
| `((note to self))` | not read |

Cmd+Enter plays the paragraph under the cursor. Cmd+Shift+Enter generates the whole thing.

### What it handles for you

Numbers, money ($5.99, ₹10 lakh, $1.5M), percentages, years (1990s, 2026), dates, times (9:30 am), ordinals, units (25km, 60fps, 4K, 1080p), phone numbers, websites and emails, abbreviations (Dr., St., e.g., vs.), roman numerals (World War II, Henry VIII), acronyms (FBI is spelled out, NASA is said as a word), and words that change sound with context (live stream, I have read, lead poisoning, a world record).

The dictionary ships with about 970 words that speech engines usually get wrong: tech brands, car and fashion brands, philosophers, psychologists, ancient history, mythology, world cities, Indian places, names and festivals, food, and foreign phrases.

## Cloning your voice

On **Voices**, press **Clone your voice** and read the passage out loud for 10 to 15 seconds, or upload any clip of you talking.

- Record in a quiet room with no music or echo. The clone copies everything, including the room.
- Speak the way you narrate your videos. The clone copies your energy and pace too.
- After it is created, check the transcript. The clone learns from your recording and those exact words, so a wrong word in the transcript lowers the quality more than anything else.
- You can make several clones (calm, hyped) and switch between them.
- Every cloned line is played back through a small speech recognizer and compared with your script. If words were skipped, repeated or garbled, that line is re-recorded automatically (up to 3 takes). Lines that still look wrong are marked "needs a listen" so you know exactly where to check.

Cloned voices are slower than built-in ones. On this M1 with 8 GB of memory, one minute of audio took about 1 minute 45 seconds to make, including the checking. A 10-minute script takes roughly 15 to 20 minutes, so start it and do something else. Built-in voices take a few seconds per minute of audio. Cloning works best in English.

## Other voices

- 41 built-in narrators: American and British English, Hindi, Spanish, French, Italian and Brazilian Portuguese.
- **Blend two voices** to get a narrator nobody else has.

## Where things are

- `data/renders/` holds every voiceover (audio, subtitles, each line)
- `data/voices/` holds your cloned voice samples
- `data/user_lexicon.json` holds the words you added
- `models/` holds the AI models (Kokoro 82M for built-in voices, Qwen3-TTS 0.6B for cloning)

## If something goes wrong

- **The page will not open:** start it with the .command file and wait for the "Booth is running" message.
- **"Voice cloning model is not downloaded":** run `bash setup.sh` in this folder.
- **A cloned line has an odd word or noise:** press redo on that line. Each take comes out a little different.
- **Low disk space:** your Mac has only a couple of GB free. Renders are small, but keep at least 3 GB free so the models can load.

Everything here is free and open source: Kokoro (Apache 2.0), Qwen3-TTS (Apache 2.0), Whisper (MIT), espeak-ng (GPL).
