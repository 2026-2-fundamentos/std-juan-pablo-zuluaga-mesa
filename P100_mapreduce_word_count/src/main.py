import shutil
import string
from pathlib import Path

ACTIVITY_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ACTIVITY_DIR / "data"
INPUT_DIR = ACTIVITY_DIR / "temp" / "input"
OUTPUT_DIR = ACTIVITY_DIR / "temp" / "output"
SUBMISSION_DIR = ACTIVITY_DIR / "submission"


def reset_dir(directory):
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)


def generate_input(n=1000):
    reset_dir(INPUT_DIR)
    for file in sorted(DATA_DIR.glob("*.txt")):
        text = file.read_text(encoding="utf-8")
        for i in range(1, n + 1):
            (INPUT_DIR / f"{file.stem}_{i:05d}.txt").write_text(text, encoding="utf-8")


def mapper(lines):
    table = str.maketrans("", "", string.punctuation)
    for line in lines:
        for word in line.lower().translate(table).split():
            yield word, 1


def reducer(pairs):
    counts = {}
    for word, value in pairs:
        counts[word] = counts.get(word, 0) + value
    return sorted(counts.items())


def read_lines():
    for file in sorted(INPUT_DIR.glob("*")):
        with open(file, encoding="utf-8") as f:
            yield from f


def write_output(result, directory):
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / "part-00000", "w", encoding="utf-8") as f:
        for word, count in result:
            f.write(f"{word}\t{count}\n")
    (directory / "_SUCCESS").write_text("", encoding="utf-8")


def main():
    generate_input()
    result = reducer(mapper(read_lines()))
    write_output(result, OUTPUT_DIR)
    write_output(result, SUBMISSION_DIR)


if __name__ == "__main__":
    main()
