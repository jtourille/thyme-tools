import os


def ensure_dir(directory):
    """
    Create a directory
    :param directory: path to create
    :return: nothing
    """

    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError as e:
        # Raising any errors except concurrent access
        if e.errno != 17:
            raise


def get_other_extension(filename, target_extension):
    """
    Get a file path with another extension
    :param filename: file path
    :param target_extension: new extension
    :return: new file path
    """

    basename, extension = os.path.splitext(filename)

    return "{0}.{1}".format(basename, target_extension)


def remove_abs(path):
    """
    Remove leading '/' from path
    :param path: input path
    :return: stripped path
    """

    if os.path.isabs(path):
        return path.lstrip("/")
    else:
        return path
