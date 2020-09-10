from sigal.image import generate_image
from sigal.settings import read_settings


def main():
    source = '0010.png'
    outname = '0010-small.png'
    settings = read_settings()
    options = None

    generate_image(source, outname, settings, options)


if __name__ == "__main__":
    main()
