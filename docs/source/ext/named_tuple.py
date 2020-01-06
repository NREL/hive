def no_namedtuple_attrib_docstring(app, what, name,
                                   obj, options, lines):
    is_namedtuple_docstring = (
            len(lines) == 1 and
            lines[0].startswith('Alias for field number')
    )
    if is_namedtuple_docstring:
        # We don't return, so we need to purge in-place
        del lines[:]


def setup(app):
    app.connect(
        'autodoc-process-docstring',
        no_namedtuple_attrib_docstring,
    )
