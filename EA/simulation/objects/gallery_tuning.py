from sims4.tuning.tunable import TunableEnumEntryimport enumimport tag
class GalleryGameplayTuning:
    EXPORT_SAVE_DATA_TO_GALLERY_TAG = TunableEnumEntry(description='\n        Reference to the tag used for marking objects that require their \n        save data to be stored in the gallery.\n        i.e. Craftables, books, etc.\n        ', tunable_type=tag.Tag, default=tag.Tag.INVALID)

class ContentSource(enum.Int, export=False):
    DEFAULT = 0
    LIBRARY = 1
    GALLERY = 2
