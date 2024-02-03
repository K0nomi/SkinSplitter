import os
import time
import re
import shutil
from distutils.dir_util import copy_tree
import configparser

import skinparser
import errors

ALL_KEYS = {'Keys1': 1, 'Keys2': 2, 'Keys3': 3, 'Keys4': 4, 'Keys5': 5, 'Keys6': 6, 'Keys7': 7, 'Keys8': 8, 'Keys9': 9, 'Keys10': 10, 'Keys12': 12, 'keys14': 14, 'keys16': 16, 'Keys18': 18}
NOTE_PROPERTIES = [('NoteImage', 'NoteImage{}'), ('NoteImageH', 'NoteImage{}H'), ('NoteImageL', 'NoteImage{}L'), ('NoteImageT', 'NoteImage{}T')]

def sanitise(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename).strip('. ').strip()

def process_config(skin_config, variants_config, styles_config, notesets_config, notes_config):
    # Create base config for variants to build from
    base_config = skinparser.SkinParser()
    base_config.update(skin_config)
    base_config.remove_section('SkinSplitter')
    base_config.remove_section('Variants')

    processed_configs = []
    for variant in skin_config['Variants']:
        # Change variant name
        processed_variant = skinparser.SkinParser()
        processed_variant.update(base_config)
        processed_variant.set('General', 'Name', skin_config.get('Variants', variant))

        # Get variant noteset
        noteset = variants_config.get_with_default(variant, 'NoteSet', fallback='Default')

        # Process the different styles
        for keymode, keymode_keycount in ALL_KEYS.items():
            style = variants_config.get_with_default(variant, keymode)
           
            if style is None:
                # Keymode not defined, skip
                # TODO: let it set defaults even when keymode is not defined
                continue

            # Get style's keycount and compare it to variant's style keycount
            style_keycount = int(styles_config.get_with_default(style, 'Keys'))
            if style_keycount != keymode_keycount:
                # Keycounts dont match, throw
                raise errors.MismatchedKeyCounts(f'Style keycount "{keymode}" in variant "[{variant}]" does not match keycount "Keys: {style_keycount}" in style "[{style}]".')

            # Create new mania section
            style_section_name = 'Mania'+str(style_keycount)
            processed_variant.add_section(style_section_name)

            # Set defaults then section configs
            processed_variant[style_section_name].update(styles_config['Default'])
            processed_variant[style_section_name].update(styles_config[style])

            # Update notes
            for note_id in range(style_keycount):
                note_key = f'Note{note_id}'

                # Get which type this note is
                raw_note_type = styles_config.get_with_default(style, note_key)

                note_type = notesets_config.get_with_default(noteset, raw_note_type, fallback=raw_note_type)

                # Remove old notes thing from new config
                processed_variant.remove_option(style_section_name, note_key)

                # Get and set note images
                # TODO: set noteimages before rest of style configs, so they can be overwritten
                for prop in NOTE_PROPERTIES:
                    note_image_prop = notes_config.get_with_default(note_type, prop[0])
                    if note_image_prop is None:
                        # Skip if property not defined in note or default
                        continue
                    processed_variant.set(style_section_name, prop[1].format(note_id), note_image_prop)

        # Finally, add it to the list
        processed_configs.append(processed_variant)

    return processed_configs

def build_skin(skin_path, watermark=None, ini_path='SkinSplitter', input_path=None, output_path='output', temp_path='_temp', auto_execute=False):
    temp_skin_path = os.path.join(temp_path, 'skin')
    # If automatically executing, use temp output
    if auto_execute:
        output_path = os.path.join(temp_path, 'output')
    # If input dir set, use that dir
    if input_path is not None:
        skin_path = os.path.join(input_path, skin_path)

    # Throw if no skin directory
    if skin_path is None:
        raise errors.UnsetSkin(f"Skin path was None.")
    if not os.path.exists(skin_path):
        raise errors.SkinNotFound(f"Skin {skin_path} was not found!")
   
    # The ini path is inside the skin directory
    ini_path = os.path.join(skin_path, ini_path)

    # Warn user if non-skinsplitter skin.ini exists
    if os.path.exists(os.path.join(skin_path, 'skin.ini')):
        print("Warning: Default skin.ini exists in skin directory, this will be ignored.")

    # Reset temp dir
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)
    os.mkdir(temp_path)
    # Add skin files to temp skin dir
    copy_tree(skin_path, temp_skin_path)

    # Parse the INI files
    configs = skinparser.parse_inis(ini_path)

    # Process the config objects
    processed_configs = process_config(*configs)

    # build skin .osks
    for c in processed_configs:
        variant_name = sanitise(c['General']['Name'])

        #Create skin.ini in temp skin dir
        skinparser.write_ini(c, os.path.join(temp_skin_path,'skin.ini'), watermark=watermark)

        # Create .osk
        output_filename = os.path.join(output_path, variant_name+'.osk')
        skin_file = shutil.make_archive(os.path.join(output_path, variant_name), 'zip', temp_skin_path)
        os.replace(skin_file, output_filename)

        # Run .osk if auto executing.
        # TODO: add option to not zip and just copy the files over if osu path specified.
        if auto_execute:
            os.startfile(output_filename)

        print(f'{variant_name} done.')

    if auto_execute:
        # Give time for osu to import
        # TODO: make this more rigorous
        time.sleep(len(processed_configs) // 1.5)
       
    # Cleanup temp dir
    shutil.rmtree(temp_path)

#TODO: add support for custom defaults (copying other skins)
