from pathlib import Path
import tarfile
import json
import sys


def walk_dir(root: Path):
    if root.is_dir():
        for x in root.iterdir():
            walk_dir(x)
    else:
        works[check_type](root)


def clean_invalidate_tarfile(x: Path):
    if not tarfile.is_tarfile(x):
        print(f'delete invalidate tar {x}')
        x.unlink()


def clean_invalidate_json(x: Path):
    print(x)
    # print(x.open().read())
    x = json.loads(x.open().read())
    print(x.keys())


if __name__ == '__main__':
    args = sys.argv
    args_amount = len(args)
    print(args_amount)
    base_path = "/tmp/data/npm/_registry"
    check_type = 0
    works = (clean_invalidate_json, clean_invalidate_tarfile)
    if args_amount == 3:
        base_path = args[1]
        check_type = int(args[2])
    elif args_amount == 2:
        check_type = int(args[1])
    f = Path(base_path)
    walk_dir(f)
