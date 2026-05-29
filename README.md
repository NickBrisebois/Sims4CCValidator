# Sims4CCValidator

Automated script for filtering out any corrupted Sims 4 CC. Files are passed in via a folder name and then any valid files are written to the output directory with the same folder structure.

Currently only supports validating .package file *headers* with the actual file content checking not quite complete. The end goal is also to validate package files fully along with .ts4scripts and images

Created for the very specific scenario of restoring Sims 4 CC that was partially recovered from a failed hard drive.


## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- git

## Installation

Clone the repository:

```bash
git clone https://github.com/NickBrisebois/Sims4CCValidator.git
```

Install the required dependencies:

```bash
uv sync
```

## Usage

Run the script:

```bash
python main.py -d ./Mods -o ./VerifiedMods
```

### Options

- `-d` or `--directory`: Directory to search for CC files
- `-o` or `--output`: Directory to save verified CC files
- `-s` or `--skip`: CC file types to skip validating (PACKAGE, SCRIPT, IMAGE)
- `-S` or `--dont-write-skipped`: For use with -s, skips writing skipped files to the output directory
- `-t` or `--dry-run`: Don't write any files to the output directory, just log the results
