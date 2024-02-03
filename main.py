import sys
import argparse

import skinsplitter
import errors

# TODO: arg for this maybe idk if that is needed
INI_PATH = 'SkinSplitter'
watermark = [
    'This skin.ini was automatically generated using SkinSplitter (made by Konomi).',
    'https://github.com/K0nomi/SkinSplitter/',
    'The contents of this skin.ini are not designed to be readable.',
    f'Check the `{INI_PATH}` folder in this skin\'s directory for the original configs.'
]

# TODO: complete args and fix silly description
# TODO: if no args are given, open gui
def parse_arguments():
    parser = argparse.ArgumentParser(description='Split them skins')
    parser.add_argument('--skin', '-s',
                        help='The name of your skin\'s folder')
    parser.add_argument('--auto-execute', '-a',  action='store_true',
                        help='Automatically execute the generated .osks to import them into osu!')
    return parser.parse_args()

def main():
    args = parse_arguments()

    try:
        skinsplitter.build_skin(args.skin, watermark, ini_path=INI_PATH, auto_execute=args.auto_execute)
    except errors.UnsetSkin:
        print("Error: Skin argument not set!")
        print(f"Please set the skin name using the following command:\n\n\t{sys.argv[0]} -s <skin_name>")

if __name__ == '__main__':
    main()
