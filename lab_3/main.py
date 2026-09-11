import os
import sys

package_dir = os.path.dirname(os.path.abspath(__file__))
if package_dir not in sys.path:
    sys.path.insert(0, package_dir)

from app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
