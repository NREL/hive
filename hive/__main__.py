import sys

from hive.app.run import run

if __name__ == "__main__":
    raise Exception("testing whether github action will see this as a failure")
    sys.exit(run() or 0)
