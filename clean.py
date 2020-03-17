from pathlib import Path
import tarfile


def walk_dir(f: Path):
    for x in f.iterdir():
        if x.is_dir():
            walk_dir(x)
        else:
            if not tarfile.is_tarfile(x):
                print(x)
                x.unlink()


if __name__ == '__main__':
    f = Path("/data/npm")
    walk_dir(f)
