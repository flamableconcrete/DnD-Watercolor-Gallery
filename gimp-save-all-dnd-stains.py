#!/usr/bin/env python2

# This is a GIMP Python plugin that I created to help me when saving stains for multiple themes simultaneously.
# It also saves a mapping of the output!

# Standard Library
import errno
import glob
import json
import os
import time

# third party
from gimpfu import *

gettext.install("gimp20-python", gimp.locale_directory, unicode=True)

ALBUMS_DIR = "C:\\Users\\flama\\PycharmProjects\\DnD-Watercolor-Gallery\\albums"
LOCATION_LOOKUP = {
    0: ["top-left", "Top-left"],
    1: ["top", "Top"],
    2: ["top-right", "Top-right"],
    3: ["top-and-bottom", "Top & Bottom"],
    4: ["left", "Left"],
    5: ["left-and-right", "Left & Right"],
    6: ["right", "Right"],
    7: ["bottom-left", "Bottom-left"],
    8: ["bottom", "Bottom"],
    9: ["bottom-right", "Bottom-right"],
    10: ["center-horizontal", "Center-horizontal"],
    11: ["center-vertical", "Center-vertical"],
}
THEME_LIST = [
    ["phb", "Player's Handbook"],
    ["dmg", "Dungeon Master's Guide"],
    ["mm", "Monster Manual"],
    ["genesys", "Genesys"],
    ["ee", "Elemental Evil"],
    ["sword_meow", "/u/swordmeow"],
    ["xgte", "Xanathar's Guide to Everything"],
    ["ice", "Generic Ice 1"],
    ["ice2", "Generic Ice 2"],
]


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def create_theme_dirs_if_needed(albums_dir):
    for theme in THEME_LIST:
        theme_slug = theme[0]
        theme_name = theme[1]
        theme_album = "{}\\{}".format(albums_dir, theme_slug)
        mkdir_p(theme_album)

        index_file = "{}\\index.md".format(theme_album)
        file_contents = "Title: {} Stains\nAuthor: Jared Ondricek (/u/flamableconcrete)\n\n## About\n\nThese images are based on the {} theme.".format(
            theme_name, theme_name
        )
        with open(index_file, "w") as file_:
            file_.write(file_contents)

        for _, location in LOCATION_LOOKUP.iteritems():
            location_slug = location[0]
            album_title = location[1]
            if location_slug == "None":
                continue
            location_album = "{}\\{}_{}".format(theme_album, theme_slug, location_slug)
            mkdir_p(location_album)

            index_file = "{}\\index.md".format(location_album)
            file_contents = (
                "Title: {}\nAuthor: Jared Ondricek (/u/flamableconcrete)".format(
                    album_title
                )
            )
            with open(index_file, "w") as file_:
                file_.write(file_contents)


def get_next_filepath_needed(album):
    os.chdir(album)
    images = glob.glob("*.png")
    num_images = len(images)
    next_image_num = num_images + 1

    # msg = "{} has {} images.".format(album, num_images)
    # pdb.gimp_message(msg)

    filename = "{:0>4}.png".format(next_image_num)
    filepath = "{}\\{}".format(album, filename)

    # msg = "{} has been saved".format(filepath)
    # pdb.gimp_message(msg)
    return filepath


def save_image(image, filepath):
    new_image = pdb.gimp_image_duplicate(image)
    layer = pdb.gimp_image_merge_visible_layers(new_image, CLIP_TO_IMAGE)
    pdb.gimp_file_save(new_image, layer, filepath, "?")
    pdb.gimp_image_delete(new_image)


def enable_theme_layer_for_image(image, theme):
    base_backgrounds_group = image.layers[0]

    for layer in base_backgrounds_group.children:
        if layer.name == theme:
            visible = True
        else:
            visible = False
        pdb.gimp_item_set_visible(layer, visible)


def set_all_layers_visible(image):
    base_backgrounds_group = image.layers[0]
    for layer in base_backgrounds_group.children:
        pdb.gimp_item_set_visible(layer, True)


def save_mask(image, location_slug):
    masks_group = image.layers[1]
    for location_mask_group in masks_group.children:
        if location_mask_group.name == location_slug:
            msg = "{} is a group".format(location_mask_group.name)
            pdb.gimp_message(msg)


def get_backup_subgroup(image, location_slug):
    masks_group = image.layers[1]
    for group in masks_group.children:
        if group.name == location_slug:
            return group


def get_next_backup_id_from_backup_group(backup_group):
    num_masks = len(backup_group.children)
    next_backup_id = num_masks + 1
    retval = "{:0>4}".format(next_backup_id)
    return retval


def backup_mask(image, location_slug):
    # get info
    base_backgrounds_group = image.layers[0]
    masks_group = image.layers[1]

    # bottom_group = masks_group.layers[0]
    backup_group = get_backup_subgroup(image, location_slug)
    orig_mask = base_backgrounds_group.mask

    # set variables
    next_backup_id = get_next_backup_id_from_backup_group(backup_group)
    new_layer_name = "{}_{}".format(location_slug, next_backup_id)
    mask_type = 0

    # create new blank layer with empty mask
    new_blank_layer = pdb.gimp_layer_new(
        image,
        image.width,
        image.height,
        RGBA_IMAGE,
        new_layer_name,
        0,
        LAYER_MODE_NORMAL,
    )
    pdb.gimp_item_set_name(new_blank_layer, new_layer_name)
    new_mask = pdb.gimp_layer_create_mask(new_blank_layer, mask_type)
    pdb.gimp_layer_add_mask(new_blank_layer, new_mask)
    pdb.gimp_image_insert_layer(image, new_blank_layer, backup_group, 0)

    # copy/paste original mask to new blank layer's mask
    pdb.gimp_edit_copy(orig_mask)
    floating_sel = pdb.gimp_edit_paste(new_mask, True)
    pdb.gimp_floating_sel_anchor(floating_sel)


def save_stains(
    image,
    layer,
    albums_dir,
    location_opt,
    phb,
    dmg,
    mm,
    genesys,
    ee,
    sword_meow,
    xgte,
    ice,
    ice2,
):
    # image = gimp.image_list()[0]

    themes = {
        "phb": phb,
        "dmg": dmg,
        "mm": mm,
        "genesys": genesys,
        "ee": ee,
        "sword_meow": sword_meow,
        "xgte": xgte,
        "ice": ice,
        "ice2": ice2,
    }

    mapping_file = "{}\\mapping.json".format(albums_dir)
    with open(mapping_file, "r") as read_file:
        mapping_data = json.load(read_file)

    create_theme_dirs_if_needed(albums_dir)

    location = LOCATION_LOOKUP[location_opt]
    location_slug = location[0]
    equivalence = {}
    for theme, save_copy in themes.iteritems():
        if not save_copy:
            continue
        enable_theme_layer_for_image(image, theme)
        album = "{}\\{}\\{}_{}".format(albums_dir, theme, theme, location_slug)
        filepath = get_next_filepath_needed(album)
        equivalence[theme] = os.path.basename(filepath)
        save_image(image, filepath)

    set_all_layers_visible(image)
    backup_mask(image, location_slug)

    # Generate mapping report
    mapping_data[location_slug].append(equivalence)
    with open(mapping_file, "w") as write_file:
        json.dump(mapping_data, write_file, indent=2)
        # json.dump(mapping_data, write_file)

    # reset for next mask
    pdb.gimp_image_set_active_layer(image, image.layers[0])
    pdb.gimp_context_set_opacity(100)


widget_params = [
    (PF_IMAGE, "image", "Input image", None),
    (PF_DRAWABLE, "drawable", "Input drawable", None),
    (
        PF_DIRNAME,
        "albums_dir",
        "Albums Directory",
        ALBUMS_DIR,
    ),
    (
        PF_OPTION,
        "location_opt",
        "Location",
        0,
        (
            "Top Left",
            "Top",
            "Top Right",
            "Top and Bottom",
            "Left",
            "Left and Right",
            "Right",
            "Bottom Left",
            "Bottom",
            "Bottom Right",
            "Center Horizontal",
            "Center Vertical",
        ),
    ),
    (PF_TOGGLE, "phb", "PHB", False),
    (PF_TOGGLE, "dmg", "DMG", False),
    (PF_TOGGLE, "mm", "MM", True),
    (PF_TOGGLE, "genesys", "Genesys", True),
    (PF_TOGGLE, "ee", "EE", True),
    (PF_TOGGLE, "sword_meow", "Sword Meow", True),
    (PF_TOGGLE, "xgte", "XGTE", True),
    (PF_TOGGLE, "ice", "Ice", True),
    (PF_TOGGLE, "ice2", "Ice2", True),
]

register(
    "python-fu-save-dnd-stains",
    N_("Save stains from multiple layers"),
    "Save a png of each layer using the same layer mask.",
    "Jared Ondricek",
    "Jared Ondricek",
    "2020",
    N_("DnD Stains..."),
    "*",
    widget_params,
    [],
    save_stains,
    # menu="<Image>/Filters/Languages/Python-Fu",
    menu="<Image>/Filters",
    domain=("gimp20-python", gimp.locale_directory),
)

main()
