import os


def ensure_dir(dir_path: str = None):
    """
    Create a directory

    Args:
        dir_path (str): directory path

    Returns:
        None
    """

    try:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
    except OSError as e:
        # Raising any errors except concurrent access
        if e.errno != 17:
            raise


def get_other_extension(filename: str = None,
                        target_extension: str = None):
    """
    Get a filename with another extension

    Args:
        filename (str): input filename
        target_extension (str): desired extension

    Returns:
        str: new filename
    """

    basename, extension = os.path.splitext(filename)

    return "{0}.{1}".format(basename, target_extension)


def remove_abs(path: str = None):
    """
    Remove leading '/' from path

    Args:
        path (str): input path

    Returns:
        str: stripped path
    """

    if os.path.isabs(path):
        return path.lstrip("/")
    else:
        return path
