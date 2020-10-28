import glob
import re
import html
from pathlib import Path

from bs4 import BeautifulSoup

files = glob.glob("build/html/*.html") + glob.glob("build/html/**/*.html")

emoji_map = {
    ':honeybee:': "&#x1F41D;",
    ':red_car:': "&#x1F698;",
    ':train:': "&#x1F686;",
}


def emojize(file: Path):
    soup = BeautifulSoup(file.open('r').read())
    for e, unicode in emoji_map.items():
        target = soup.find_all(text=re.compile(rf"{e}"))
        for t in target:
            t.replace_with(t.replace(f"{e}", html.unescape(unicode)))

    file.write_text(str(soup))


if __name__ == "__main__":
    for f in files:
        print(f"emojizing file {f}")
        emojize(Path(f))
